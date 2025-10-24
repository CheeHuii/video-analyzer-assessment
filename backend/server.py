# backend/server.py
import time
import uuid
import json
from concurrent import futures
import grpc

from backend.protos import chat_pb2_grpc, chat_pb2  # generated code
from backend.db import init_db, store_message, get_history, now_ms
from backend.attachments_store import save_attachment_bytes

# Initialize DB
init_db()

class ChatServiceServicer(chat_pb2_grpc.ChatServiceServicer):
    def SendMessage(self, request, context):
        # store the incoming message
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
        # optionally trigger agent(s) here; for SendMessage we return stored message
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
        Example: stream a "generated" agent response to the user
        This example uses a simple simulated generator. Replace this block
        with calls to local model inference that yield tokens / partial strings.
        """
        user_text = request.message.text or ""
        conv_id = request.conversation_id or request.message.conversation_id or "default"
        # store user message first
        user_stored = {
            "id": request.message.id or uuid.uuid4().hex,
            "conversation_id": conv_id,
            "sender": request.message.sender or "user",
            "text": user_text,
            "created_at": request.message.created_at or now_ms(),
            "confidence": request.message.confidence if request.message.confidence != 0 else None,
            "needs_clarification": request.message.needs_clarification,
            "attachments": list(request.message.attachments),
            "metadata_json": json.loads(request.message.metadata_json) if request.message.metadata_json else {}
        }
        store_message(user_stored)

        # Example: local "agent" will respond; you should plug in OpenVINO/HF model generation here.
        # We'll simulate streaming by chunking a reply string.
        reply_text = f"Simulated agent reply summarizing: {user_text[:200]}"
        chunk_size = 40
        for i in range(0, len(reply_text), chunk_size):
            chunk = reply_text[i:i+chunk_size]
            yield chat_pb2.StreamResponse(partial_text=chunk, done=False)
            time.sleep(0.05)  # small delay to emulate streaming

        # when done, persist final agent message
        agent_msg = {
            "id": uuid.uuid4().hex,
            "conversation_id": conv_id,
            "sender": "agent",
            "text": reply_text,
            "created_at": now_ms(),
            "confidence": 0.9,
            "needs_clarification": False,
            "attachments": [],
            "metadata_json": {}
        }
        store_message(agent_msg)
        # yield final message as Message payload + done=True
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

def serve(port=50051):
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    chat_pb2_grpc.add_ChatServiceServicer_to_server(ChatServiceServicer(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    print(f"gRPC server listening on {port}")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.stop(0)

if __name__ == "__main__":
    serve()
