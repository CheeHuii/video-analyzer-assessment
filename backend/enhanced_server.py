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
from backend.attachments_store import save_attachment_bytes
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
        # Optional: Load LLM for query understanding
        self.llm = None
        self._init_mcp_connection()
    
    def _init_mcp_connection(self):
        """Initialize connection to MCP server."""
        try:
            self.mcp_channel = grpc.insecure_channel(self.mcp_addr)
            self.mcp_stub = mgr_grpc.AgentManagerStub(self.mcp_channel)
            print(f"Connected to MCP server at {self.mcp_addr}")
        except Exception as e:
            print(f"Failed to connect to MCP server: {e}")
    
    def _parse_user_intent(self, text: str, attachments: list) -> dict:
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
            return {
                "intent": "transcribe",
                "agent_type": common_pb.AgentType.AGENT_TRANSCRIPTION,
                "video_path": video_attachment,
                "needs_processing": True
            }
        elif any(keyword in text_lower for keyword in ['detect', 'objects', 'vision', 'what do you see', 'analyze frame', 'visual']):
            return {
                "intent": "analyze_video",
                "agent_type": common_pb.AgentType.AGENT_VISION,
                "video_path": video_attachment,
                "needs_processing": True
            }
        elif any(keyword in text_lower for keyword in ['summary', 'pdf', 'powerpoint', 'pptx', 'slides', 'report']):
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
        # Ingest video (extract audio, frames, metadata)
        print(f"Ingesting video: {video_path}")
        meta = ingest_video(video_path, sample_ms=500)
        video_id = meta["video_id"]
        video_dir = Path("data") / "videos" / video_id
        meta_path = video_dir / "meta.json"
        
        task_ids = []
        
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
            file_ref = common_pb.FileRef(
                uri=str(meta_path),
                mime="application/json",
                size_bytes=os.path.getsize(meta_path)
            )
            task_req = common_pb.TaskRequest(
                task_id=task_id,
                agent_type_hint=a_type,
                input=file_ref
            )
            
            try:
                response = self.mcp_stub.AssignTask(task_req)
                if response.accepted:
                    task_ids.append(task_id)
                    print(f"Task {task_id} assigned to {response.assigned_agent_id}")
                else:
                    print(f"Task {task_id} rejected: {response.message}")
            except Exception as e:
                print(f"Failed to assign task: {e}")
        
        return {
            "video_id": video_id,
            "task_ids": task_ids,
            "status": "processing" if task_ids else "failed"
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
        intent_info = self._parse_user_intent(user_text, attachments)
        
        if intent_info["needs_processing"] and intent_info["video_path"]:
            # Process video and submit to agents
            yield chat_pb2.StreamResponse(
                partial_text="Processing video...",
                done=False
            )
            
            try:
                result = self._process_video_and_submit_task(
                    intent_info["video_path"],
                    intent_info["agent_type"]
                )
                
                if result["status"] == "processing":
                    response_text = f"Video analysis started (ID: {result['video_id']}). "
                    response_text += f"Processing {len(result['task_ids'])} tasks. "
                    response_text += "Results will be available shortly."
                    
                    # Stream the response
                    chunk_size = 40
                    for i in range(0, len(response_text), chunk_size):
                        chunk = response_text[i:i+chunk_size]
                        yield chat_pb2.StreamResponse(partial_text=chunk, done=False)
                        time.sleep(0.05)
                else:
                    response_text = "Failed to process video. Please check the logs."
                    yield chat_pb2.StreamResponse(partial_text=response_text, done=False)
            except Exception as e:
                error_text = f"Error processing video: {str(e)}"
                yield chat_pb2.StreamResponse(partial_text=error_text, done=False)
        else:
            # Simple chat response (could integrate LLM here)
            response_text = f"Received your message: {user_text[:100]}"
            if not intent_info["needs_processing"]:
                response_text = "I can help you analyze videos! Upload a video and ask me to transcribe, detect objects, or generate a summary."
            
            chunk_size = 40
            for i in range(0, len(response_text), chunk_size):
                chunk = response_text[i:i+chunk_size]
                yield chat_pb2.StreamResponse(partial_text=chunk, done=False)
                time.sleep(0.05)
        
        # Store agent message
        agent_msg = {
            "id": uuid.uuid4().hex,
            "conversation_id": conv_id,
            "sender": "agent",
            "text": response_text,
            "created_at": now_ms(),
            "confidence": 0.8,
            "needs_clarification": False,
            "attachments": [],
            "metadata_json": intent_info
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
