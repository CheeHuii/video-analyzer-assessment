#!/usr/bin/env python3
"""
Main entry point for the Video Analyzer backend.
Starts all required services:
1. MCP Server (Agent Manager) - manages agents and tasks
2. Chat Service - handles user chat interactions
3. Agents - transcription, vision, generation

All services run in parallel using asyncio.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Ensure backend is in path
sys.path.insert(0, str(Path(__file__).parent))

from backend.mcp_server import serve_async as serve_mcp
from backend.enhanced_server import serve as serve_chat
from backend.agents.transcription_agent import TranscriptionAgent
from backend.agents.vision_agent import VisionAgent
from backend.agents.generation_agent import GenerationAgent

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("main")


# Global tasks for cleanup
tasks = []


async def start_agents(mcp_addr: str = "localhost:50052"):
    """
    Start all agents and connect them to the MCP server.
    Each agent runs its heartbeat loop.
    """
    logger.info("Starting agents...")
    
    # Create agents
    transcription_agent = TranscriptionAgent(
        name="transcription-agent-1",
        server_addr=mcp_addr,
        model_size="base",  # whisper model size
        device="cpu"
    )
    
    vision_agent = VisionAgent(
        name="vision-agent-1",
        server_addr=mcp_addr,
        model_path="backend/models/yolov8n.onnx"
    )
    
    generation_agent = GenerationAgent(
        name="generation-agent-1",
        server_addr=mcp_addr
    )
    
    # Start agents (they will register and maintain heartbeat)
    agent_tasks = [
        asyncio.create_task(transcription_agent.run()),
        asyncio.create_task(vision_agent.run()),
        asyncio.create_task(generation_agent.run())
    ]
    
    logger.info("Agents started and registered with MCP server")
    
    # Wait for all agents
    await asyncio.gather(*agent_tasks)


async def start_mcp_server(host: str = "[::]", port: int = 50052):
    """Start the MCP (Agent Manager) server."""
    logger.info(f"Starting MCP server on {host}:{port}")
    await serve_mcp(host, port)


async def start_chat_server(port: int = 50051, mcp_addr: str = "localhost:50052"):
    """
    Start the Chat service server.
    Note: The original serve() is synchronous, we need to wrap it or make it async.
    For now, we'll run it in an executor.
    """
    logger.info(f"Starting Chat server on port {port}")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, serve_chat, port, mcp_addr)


async def main():
    """
    Main async function that starts all services.
    """
    logger.info("=" * 60)
    logger.info("Starting Video Analyzer Backend")
    logger.info("=" * 60)
    
    # Create tasks for all services
    mcp_task = asyncio.create_task(start_mcp_server("[::]", 50052))
    chat_task = asyncio.create_task(start_chat_server(50051, "localhost:50052"))
    
    # Give servers time to start
    await asyncio.sleep(2)
    
    # Start agents (they will connect to MCP server)
    agents_task = asyncio.create_task(start_agents("localhost:50052"))
    
    # Store tasks for cleanup
    tasks.extend([mcp_task, chat_task, agents_task])
    
    logger.info("=" * 60)
    logger.info("All services started successfully!")
    logger.info("MCP Server (Agent Manager): [::]::50052")
    logger.info("Chat Service: [::]::50051")
    logger.info("Agents: transcription, vision, generation")
    logger.info("=" * 60)
    
    # Wait for all tasks
    try:
        await asyncio.gather(*tasks)
    except asyncio.CancelledError:
        logger.info("Shutting down services...")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("All services stopped")


def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully."""
    logger.info(f"Received signal {signum}, initiating shutdown...")
    for task in tasks:
        task.cancel()
    sys.exit(0)


if __name__ == "__main__":
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
