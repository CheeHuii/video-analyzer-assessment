import sys
import json
import grpc
import argparse
from backend.protos import chat_pb2, chat_pb2_grpc

parser = argparse.ArgumentParser()
parser.add_argument("--addr")
parser.add_argument("--conversation")
parser.add_argument("--sender")
parser.add_argument("--text")
args = parser.parse_args()

channel = grpc.insecure_channel(args.addr)
stub = chat_pb2_grpc.ChatServiceStub(channel)

req = chat_pb2.ChatRequest(
    conversation_id=args.conversation,
    sender=args.sender,
    text=args.text,
)

for resp in stub.StreamResponses(req):
    print(json.dumps({
        "type": "message",
        "sender": resp.sender,
        "text": resp.text,
        "confidence": resp.confidence
    }), flush=True)
