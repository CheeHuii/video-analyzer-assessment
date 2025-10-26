#!/usr/bin/env python3
"""
Simple test script to verify basic backend services can start.
This uses the simpler original server.py which doesn't require ML dependencies.
"""
import sys
import asyncio
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from backend.server import serve


if __name__ == "__main__":
    print("Starting simple chat server on port 50051...")
    print("Press Ctrl+C to stop")
    try:
        serve(port=50051)
    except KeyboardInterrupt:
        print("\nServer stopped")
