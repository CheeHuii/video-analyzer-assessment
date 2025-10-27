# backend/enhanced_server.py
"""
Enhanced Chat Server that integrates with:
1. Agent Manager (MCP) for task orchestration
2. LLM for intelligent query understanding and routing
3. Video ingestion pipeline
"""
import time
import uuid
import json
import os
import hashlib
import asyncio
import grpc
from concurrent import futures
from pathlib import Path
from typing import Optional

from backend.protos import chat_pb2_grpc, chat_pb2
from backend.protos import agent_manager_pb2 as mgr_pb2
from backend.protos import agent_manager_pb2_grpc as mgr_grpc
from backend.protos import common_pb2 as common_pb
from backend.db import init_db, store_message, get_history, now_ms
from backend.ingest import ingest_video

# Initialize DB
init_db()


class EnhancedChatServicer(chat_pb2_grpc.ChatServiceServicer):
    """
    Enhanced chat service that can route user queries to appropriate agents.
    """
    
    def __init__(self, mcp_addr: str = "localhost:50052"):
        self.mcp_addr = mcp_addr
        self.mcp_channel = None
        self.mcp_stub = None
        self.llm = None
        self.rag = None
        self._init_mcp_connection()
        self._init_rag()
        # If RAG is initialized, reuse its LLM for general fallbacks
        try:
            if self.rag is not None and getattr(self.rag, 'llm', None) is not None:
                self.llm = self.rag.llm
        except Exception:
            pass
    
    def _init_mcp_connection(self):
        """Initialize connection to MCP server."""
        try:
            self.mcp_channel = grpc.insecure_channel(self.mcp_addr)
            self.mcp_stub = mgr_grpc.AgentManagerStub(self.mcp_channel)
            print(f"Connected to MCP server at {self.mcp_addr}")
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")

    def _init_rag(self):
        """Initialize RAG stack if local models are available."""
        try:
            from backend.llm.rag import RAG
            # try first model dir, then fallback
            base = Path("backend/models/llm")
            candidates = [base/"hf_llm", base/"hf_llm2"]
            model_dir = None
            for c in candidates:
                if c.exists():
                    model_dir = str(c)
                    break
            if model_dir is None:
                print("[RAG] No local LLM model directory found; RAG disabled")
                return
            self.rag = RAG(model_dir_for_llm=model_dir)
            print(f"[RAG] initialized with model {model_dir}")
        except Exception as e:
            print(f"[RAG] init failed: {e}")
    
    def _get_latest_video_path(self, conversation_id: str) -> Optional[str]:
        """Find the most recent video path from history or filesystem fallback."""
        try:
            rows = get_history(conversation_id, limit=100, offset=0)
        except Exception:
            rows = []
        # iterate from newest to oldest
        for r in reversed(rows):
            # attachments stored as list of strings
            for a in r.get("attachments", []) or []:
                if not isinstance(a, str):
                    continue
                a_clean = a.strip().strip('"')
                if not (a_clean.endswith('.mp4') or a_clean.endswith('.avi') or a_clean.endswith('.mov')):
                    continue
                # must exist and not be a loose file directly under data/videos root
                p = Path(a_clean)
                if not p.exists():
                    continue
                try:
                    # skip files that live directly under .../data/videos (prefer subfolder/raw.mp4)
                    if p.parent.name == 'videos' and p.parent.parent.name == 'data':
                        continue
                except Exception:
                    pass
                return a_clean
        # Fallback to filesystem if not found in history
        try:
            base = Path("data") / "videos"
            if not base.exists():
                return None
            # Only consider raw.mp4 inside subfolders; ignore loose files in videos root
            candidates = []
            for sub in base.iterdir():
                if sub.is_dir():
                    rp = sub / "raw.mp4"
                    if rp.exists():
                        candidates.append(rp)
            if not candidates:
                return None
            # pick most recent by mtime
            latest = max(candidates, key=lambda p: p.stat().st_mtime)
            return str(latest)
        except Exception:
            return None

    def _parse_user_intent(self, text: str, attachments: list, conversation_id: Optional[str] = None) -> dict:
        """
        Parse user message to determine intent and required agent.
        Returns: {
            "intent": "transcribe" | "analyze_video" | "generate_summary" | "chat",
            "agent_type": AgentType enum,
            "video_path": str if attachment is video,
            "needs_processing": bool
        }
        """
        text_lower = text.lower()
        
        # Check for video attachments
        video_attachment = None
        for att in attachments:
            if att.endswith('.mp4') or att.endswith('.avi') or att.endswith('.mov'):
                video_attachment = att
                break
        
        # Determine intent based on keywords
        if any(keyword in text_lower for keyword in ['transcribe', 'transcript', 'what was said', 'speech']):
            if not video_attachment and conversation_id:
                video_attachment = self._get_latest_video_path(conversation_id)
            return {
                "intent": "transcribe",
                "agent_type": common_pb.AgentType.AGENT_TRANSCRIPTION,
                "video_path": video_attachment,
                "needs_processing": True
            }
        elif any(keyword in text_lower for keyword in ['detect', 'object', 'objects', 'vision', 'what do you see', 'analyze frame', 'visual', 'table']):
            if not video_attachment and conversation_id:
                video_attachment = self._get_latest_video_path(conversation_id)
            return {
                "intent": "analyze_video",
                "agent_type": common_pb.AgentType.AGENT_VISION,
                "video_path": video_attachment,
                "needs_processing": True
            }
        elif any(keyword in text_lower for keyword in ['summary', 'summarize', 'summarise', 'pdf', 'powerpoint', 'ppt', 'pptx', 'slides', 'report']):
            if not video_attachment and conversation_id:
                video_attachment = self._get_latest_video_path(conversation_id)
            return {
                "intent": "generate_summary",
                "agent_type": common_pb.AgentType.AGENT_GENERATION,
                "video_path": video_attachment,
                "needs_processing": True
            }
        elif video_attachment:
            # If there's a video but no specific intent, do full processing
            return {
                "intent": "full_analysis",
                "agent_type": None,  # Will trigger all agents
                "video_path": video_attachment,
                "needs_processing": True
            }
        else:
            # Simple chat without agent processing
            return {
                "intent": "chat",
                "agent_type": None,
                "video_path": None,
                "needs_processing": False
            }
    
    def _process_video_and_submit_task(self, video_path: str, agent_type: Optional[int]) -> dict:
        """
        Ingest video and submit task to appropriate agent(s).
        Returns: {
            "video_id": str,
            "task_ids": [str],
            "status": str
        }
        """
        def _stable_id_for_path(p: str) -> str:
            try:
                st = os.stat(p)
                key = f"{os.path.basename(p)}|{st.st_size}|{int(st.st_mtime_ns)}".encode("utf-8", errors="ignore")
            except Exception:
                key = p.encode("utf-8", errors="ignore")
            return hashlib.sha1(key).hexdigest()[:8]

        # If path is already inside data/videos/<id>/..., reuse that id
        abs_path = str(Path(video_path).resolve())
        base_videos = str((Path("data") / "videos").resolve())
        reuse_id = None
        if abs_path.startswith(base_videos):
            # find the immediate folder after videos
            try:
                parts = Path(abs_path).parts
                vids_parts = Path(base_videos).parts
                if len(parts) > len(vids_parts):
                    candidate_id = parts[len(vids_parts)]
                    candidate_dir = Path(base_videos) / candidate_id
                    if (candidate_dir / "meta.json").exists():
                        reuse_id = candidate_id
            except Exception:
                pass

        if reuse_id:
            video_id = reuse_id
            video_dir = Path("data") / "videos" / video_id
            meta_path = video_dir / "meta.json"
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
        else:
            # compute stable id and ingest only if needed
            video_id = _stable_id_for_path(abs_path)
            video_dir = Path("data") / "videos" / video_id
            meta_path = video_dir / "meta.json"
            if meta_path.exists():
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            else:
                print(f"Ingesting video: {video_path} -> id {video_id}")
                meta = ingest_video(abs_path, video_id=video_id, sample_ms=500)
        
        task_ids = []
        task_map = {}  # task_id -> agent_type_name
        
        if agent_type is None:
            # Full analysis: submit to all agents
            agent_types = [
                common_pb.AgentType.AGENT_TRANSCRIPTION,
                common_pb.AgentType.AGENT_VISION,
                common_pb.AgentType.AGENT_GENERATION
            ]
        else:
            agent_types = [agent_type]
        
        # Submit tasks to each agent
        for a_type in agent_types:
            task_id = str(uuid.uuid4())
            # Vision agent expects a directory (video_dir) to find frames;
            # others can consume meta.json
            if a_type == common_pb.AgentType.AGENT_VISION:
                input_uri = str(video_dir)
                mime = "inode/directory"
                size_b = 0
            else:
                input_uri = str(meta_path)
                mime = "application/json"
                size_b = int(os.path.getsize(str(meta_path)))

            file_ref = common_pb.FileRef(
                uri=input_uri,
                mime=mime,
                size_bytes=size_b
            )
            task_req = common_pb.TaskRequest(
                task_id=task_id,
                agent_type_hint=common_pb.AgentType.Name(a_type),
                input=file_ref
            )
            
            try:
                response = self.mcp_stub.AssignTask(task_req)
                if response.accepted:
                    task_ids.append(task_id)
                    task_map[task_id] = common_pb.AgentType.Name(a_type)
                    print(f"Task {task_id} assigned to {response.assigned_agent_id}")
                else:
                    print(f"Task {task_id} rejected: {response.message}")
            except Exception as e:
                print(f"Failed to assign task: {e}")
        
        return {
            "video_id": video_id,
            "task_ids": task_ids,
            "status": "processing" if task_ids else "failed",
            "task_map": task_map
        }
    
    def SendMessage(self, request, context):
        """Handle non-streaming message."""
        msg = request.message
        stored = {
            "id": msg.id or uuid.uuid4().hex,
            "conversation_id": request.conversation_id or msg.conversation_id or "default",
            "sender": msg.sender or "user",
            "text": msg.text,
            "created_at": msg.created_at or now_ms(),
            "confidence": msg.confidence if msg.confidence != 0 else None,
            "needs_clarification": msg.needs_clarification,
            "attachments": list(msg.attachments),
            "metadata_json": json.loads(msg.metadata_json) if msg.metadata_json else {}
        }
        store_message(stored)
        
        resp_msg = chat_pb2.Message(
            id=stored["id"],
            conversation_id=stored["conversation_id"],
            sender=stored["sender"],
            text=stored["text"],
            created_at=stored["created_at"],
            confidence=stored["confidence"] or 0.0,
            needs_clarification=stored["needs_clarification"],
            attachments=stored["attachments"],
            metadata_json=json.dumps(stored["metadata_json"])
        )
        return chat_pb2.SendMessageResponse(stored_message=resp_msg)

    def GetHistory(self, request, context):
        """Fetch conversation history."""
        conv_id = request.conversation_id or "default"
        rows = get_history(conv_id, limit=request.limit or 100, offset=request.offset or 0)
        msgs = []
        for r in rows:
            m = chat_pb2.Message(
                id=r["id"],
                conversation_id=r["conversation_id"],
                sender=r["sender"],
                text=r["text"] or "",
                created_at=r["created_at"],
                confidence=r["confidence"] or 0.0,
                needs_clarification=r["needs_clarification"],
                attachments=r["attachments"],
                metadata_json=json.dumps(r["metadata_json"])
            )
            msgs.append(m)
        return chat_pb2.GetHistoryResponse(messages=msgs)

    def StreamResponses(self, request, context):
        """
        Stream intelligent agent responses based on user query.
        This method:
        1. Analyzes user intent
        2. Routes to appropriate agent if needed
        3. Streams progress and results back to user
        """
        user_text = request.message.text or ""
        conv_id = request.conversation_id or request.message.conversation_id or "default"
        attachments = list(request.message.attachments)
        
        # Store user message
        user_stored = {
            "id": request.message.id or uuid.uuid4().hex,
            "conversation_id": conv_id,
            "sender": request.message.sender or "user",
            "text": user_text,
            "created_at": request.message.created_at or now_ms(),
            "confidence": request.message.confidence if request.message.confidence != 0 else None,
            "needs_clarification": request.message.needs_clarification,
            "attachments": attachments,
            "metadata_json": json.loads(request.message.metadata_json) if request.message.metadata_json else {}
        }
        store_message(user_stored)
        
        # Parse user intent
        intent_info = self._parse_user_intent(user_text, attachments, conv_id)
        
        if intent_info["needs_processing"] and intent_info["video_path"]:
            # Process video and submit to agents
            yield chat_pb2.StreamResponse(
                partial_text="Processing video...",
                done=False
            )
            
            try:
                # Normalize path to plain string without surrounding quotes
                vpath = intent_info["video_path"]
                if not isinstance(vpath, str):
                    vpath = str(vpath)
                vpath = vpath.strip().strip('"')
                if not os.path.exists(vpath):
                    # try to resolve to latest known good raw.mp4
                    alt = self._get_latest_video_path(conv_id)
                    if alt and os.path.exists(alt):
                        vpath = alt
                    else:
                        raise FileNotFoundError(f"Video not found: {vpath}")

                result = self._process_video_and_submit_task(
                    vpath,
                    intent_info["agent_type"]
                )
                
                if result["status"] == "processing":
                    response_text = f"Video analysis started (ID: {result['video_id']}). Processing {len(result['task_ids'])} tasks."
                    # initial message
                    chunk_size = 60
                    for i in range(0, len(response_text), chunk_size):
                        chunk = response_text[i:i+chunk_size]
                        yield chat_pb2.StreamResponse(partial_text=chunk, done=False)
                        time.sleep(0.03)

                    # Stream progress per task and capture completions
                    completed_outputs = []
                    for tid in result["task_ids"]:
                        # announce agent type for visual cue
                        aname = result.get("task_map", {}).get(tid, "AGENT")
                        try:
                            yield chat_pb2.StreamResponse(partial_text=f"\n{aname}: started", done=False)
                        except Exception:
                            pass
                        try:
                            req = mgr_pb2.TaskProgressRequest(task_id=tid)
                            for upd in self.mcp_stub.StreamProgress(req):
                                # message may contain "Completed:<path>" or "Failed:<error>"
                                msg = upd.message or ""
                                if msg.startswith("Completed:"):
                                    out_path = msg.split(":", 1)[1]
                                    completed_outputs.append(out_path)
                                    yield chat_pb2.StreamResponse(partial_text=f"\n{aname}: completed.", done=False)
                                    break
                                elif msg.startswith("Failed:"):
                                    err = msg.split(":", 1)[1]
                                    yield chat_pb2.StreamResponse(partial_text=f"\n{aname}: failed: {err}", done=False)
                                    break
                                else:
                                    # progress update
                                    yield chat_pb2.StreamResponse(partial_text=f"\n{aname}: {upd.percent}%", done=False)
                        except Exception as e:
                            yield chat_pb2.StreamResponse(partial_text=f"\n{aname}: progress stream error: {e}", done=False)

                    if completed_outputs:
                        # Summarize outputs location back to user
                        summary = "\nOutputs:\n" + "\n".join(f"- {p}" for p in completed_outputs)
                        yield chat_pb2.StreamResponse(partial_text=summary, done=False)
                else:
                    response_text = "Failed to process video. Please check the logs."
                    yield chat_pb2.StreamResponse(partial_text=response_text, done=False)
            except Exception as e:
                error_text = f"Error processing video: {str(e)}"
                yield chat_pb2.StreamResponse(partial_text=error_text, done=False)
        else:
            # Simple chat response (could integrate LLM here)
            if intent_info.get("needs_processing") and not intent_info.get("video_path"):
                response_text = "I found no recent video to process. Please upload a video or reference its path."
            else:
                # If RAG is available and we have a recent video, answer using RAG
                # Require a video to be uploaded before chat
                vpath = intent_info.get("video_path") or self._get_latest_video_path(conv_id)
                if not vpath or not os.path.exists(vpath):
                    response_text = "Please upload a video first, then ask me to transcribe, detect objects, or summarize it."
                else:
                    response_text = ""
                    used_rag = False
                    try:
                        if self.rag is not None:
                            vdir = Path(vpath).parent if Path(vpath).is_file() else Path(vpath)
                            ans = self.rag.answer(str(vdir), user_text)
                            response_text = ans.get("answer") or ""
                            used_rag = True
                    except Exception as e:
                        print(f"[RAG] answer failed: {e}")
                        used_rag = False
                    if not used_rag:
                        response_text = response_text or "I can help you analyze videos! Try: 'transcribe', 'summarize to pdf/ppt', or 'detect objects'."
            
            chunk_size = 40
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i+chunk_size]
                yield chat_pb2.StreamResponse(partial_text=chunk, done=False)
                time.sleep(0.05)
        
        # Store agent message
        # Include video_id in metadata if processing started
        meta_copy = dict(intent_info)
        try:
            # attempt to include last computed video_id when we processed
            if 'result' in locals() and isinstance(result, dict) and result.get('video_id'):
                meta_copy['video_id'] = result['video_id']
        except Exception:
            pass

        agent_msg = {
            "id": uuid.uuid4().hex,
            "conversation_id": conv_id,
            "sender": "agent",
            "text": response_text,
            "created_at": now_ms(),
            "confidence": 0.8,
            "needs_clarification": False,
            "attachments": [],
            "metadata_json": meta_copy
        }
        store_message(agent_msg)
        
        # Final message
        msg_proto = chat_pb2.Message(
            id=agent_msg["id"],
            conversation_id=agent_msg["conversation_id"],
            sender=agent_msg["sender"],
            text=agent_msg["text"],
            created_at=agent_msg["created_at"],
            confidence=agent_msg["confidence"],
            needs_clarification=agent_msg["needs_clarification"],
            attachments=agent_msg["attachments"],
            metadata_json=json.dumps(agent_msg["metadata_json"])
        )
        yield chat_pb2.StreamResponse(message=msg_proto, done=True)


def serve(port=50051, mcp_addr="localhost:50052"):
    """Start the enhanced chat service."""
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(
        EnhancedChatServicer(mcp_addr), 
        server
    )
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"Enhanced gRPC Chat server listening on port {port}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop(0)


if __name__ == "__main__":
    serve()
