import asyncio
from backend.chat_service import serve as serve_chat
from backend.agent_manager_service import serve_async as serve_mcp

async def main():
    # Run both services
    chat_server = asyncio.create_task(serve_chat(port=50051))
    mcp_server = asyncio.create_task(serve_mcp(port=50052))
    
    try:
        # Wait for both
        await asyncio.gather(chat_server, mcp_server)
    except KeyboardInterrupt:
        print("Shutting down servers...")

if __name__ == "__main__":
    asyncio.run(main())