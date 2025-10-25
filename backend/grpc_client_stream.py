#!/usr/bin/env python3
"""
gRPC client script for streaming chat responses.
Called by Tauri frontend via subprocess.
Outputs JSON lines to stdout for the frontend to consume.
"""
import sys
import json
import argparse
import asyncio
import grpc

from backend.protos import chat_pb2
from backend.protos import chat_pb2_grpc


async def stream_chat(addr: str, conversation_id: str, sender: str, text: str):
    """
    Connect to gRPC ChatService and stream responses.
    Each chunk is printed as a JSON line to stdout.
    """
    # Create channel and stub
    channel = grpc.aio.insecure_channel(addr)
    stub = chat_pb2_grpc.ChatServiceStub(channel)
    
    # Create message request
    message = chat_pb2.Message(
        sender=sender,
        text=text,
        conversation_id=conversation_id
    )
    
    request = chat_pb2.SendMessageRequest(
        conversation_id=conversation_id,
        message=message,
        stream_responses=True
    )
    
    try:
        # Stream responses
        async for response in stub.StreamResponses(request):
            # Convert to dict for JSON serialization
            response_dict = {}
            
            if response.HasField("partial_text"):
                response_dict["partial_text"] = response.partial_text
            elif response.HasField("message"):
                msg = response.message
                response_dict["message"] = {
                    "id": msg.id,
                    "conversation_id": msg.conversation_id,
                    "sender": msg.sender,
                    "text": msg.text,
                    "created_at": msg.created_at,
                    "confidence": msg.confidence,
                    "needs_clarification": msg.needs_clarification,
                    "attachments": list(msg.attachments),
                    "metadata_json": msg.metadata_json
                }
            
            response_dict["done"] = response.done
            
            # Print as JSON line to stdout
            print(json.dumps(response_dict), flush=True)
            
            if response.done:
                break
    except grpc.RpcError as e:
        error_dict = {
            "error": str(e),
            "code": e.code().name if hasattr(e, 'code') else "UNKNOWN"
        }
        print(json.dumps(error_dict), flush=True)
    finally:
        await channel.close()


def main():
    parser = argparse.ArgumentParser(description="Stream chat responses via gRPC")
    parser.add_argument("--addr", required=True, help="gRPC server address (e.g., localhost:50051)")
    parser.add_argument("--conversation", required=True, help="Conversation ID")
    parser.add_argument("--sender", default="user", help="Sender name")
    parser.add_argument("--text", required=True, help="Message text")
    
    args = parser.parse_args()
    
    # Run async function
    asyncio.run(stream_chat(args.addr, args.conversation, args.sender, args.text))


if __name__ == "__main__":
    main()
