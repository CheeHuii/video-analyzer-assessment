#!/usr/bin/env python3
"""
gRPC client script for fetching chat history.
Called by Tauri frontend via subprocess.
Outputs JSON to stdout containing the history response.
"""
import sys
import json
import argparse
import asyncio
import grpc

from backend.protos import chat_pb2
from backend.protos import chat_pb2_grpc


async def get_history(addr: str, conversation_id: str, limit: int = 100, offset: int = 0):
    """
    Connect to gRPC ChatService and fetch conversation history.
    Returns JSON output to stdout.
    """
    # Create channel and stub
    channel = grpc.aio.insecure_channel(addr)
    stub = chat_pb2_grpc.ChatServiceStub(channel)
    
    # Create request
    request = chat_pb2.GetHistoryRequest(
        conversation_id=conversation_id,
        limit=limit,
        offset=offset
    )
    
    try:
        # Get history
        response = await stub.GetHistory(request)
        
        # Convert messages to dict
        messages = []
        for msg in response.messages:
            messages.append({
                "id": msg.id,
                "conversation_id": msg.conversation_id,
                "sender": msg.sender,
                "text": msg.text,
                "created_at": msg.created_at,
                "confidence": msg.confidence,
                "needs_clarification": msg.needs_clarification,
                "attachments": list(msg.attachments),
                "metadata_json": msg.metadata_json
            })
        
        result = {"messages": messages}
        
        # Print as JSON to stdout
        print(json.dumps(result), flush=True)
    except grpc.RpcError as e:
        error_dict = {
            "error": str(e),
            "code": e.code().name if hasattr(e, 'code') else "UNKNOWN",
            "messages": []
        }
        print(json.dumps(error_dict), flush=True)
    finally:
        await channel.close()


def main():
    parser = argparse.ArgumentParser(description="Fetch chat history via gRPC")
    parser.add_argument("--addr", required=True, help="gRPC server address (e.g., localhost:50051)")
    parser.add_argument("--conversation", required=True, help="Conversation ID")
    parser.add_argument("--limit", type=int, default=100, help="Max messages to fetch")
    parser.add_argument("--offset", type=int, default=0, help="Offset for pagination")
    
    args = parser.parse_args()
    
    # Run async function
    asyncio.run(get_history(args.addr, args.conversation, args.limit, args.offset))


if __name__ == "__main__":
    main()
