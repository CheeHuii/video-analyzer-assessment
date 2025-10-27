# video-analyzer-assessment
This is a project for test assessment
Runs fully offline using OpenVINO-optimized local models and MCP agents.

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Fast setup and testing
- **[Note.md](NOTE.md)** - List of what works and what does not, enhancement can be done
- **[check_setup.py](check_setup.py)** - Verify your environment

## Features (planned)
- Upload and process `.mp4` videos locally.
- Natural-language chat to query video content (transcribe, summarize, detect objects, etc.).
- PDF and PowerPoint generation.
- Persistent history.
- Fully local AI inference with modular agents.

## Repo Structure
- **frontend/** – React + Tauri chat UI (✅ wired to backend)
- **backend/** – Python gRPC services and agents (✅ integrated)
  - `server.py` - Simple chat service
  - `enhanced_server.py` - Chat with agent integration
  - `mcp_server.py` - Agent manager (MCP)
  - `grpc_client_*.py` - Client scripts for Tauri
  - `agents/` - Transcription, vision, generation agents
- **protos/** – gRPC service definitions
- **main.py** – Start all backend services
- **test_simple_server.py** – Test server for development
- **check_setup.py** – Verify environment setup

## Quick Start
```bash
# Check your setup
python check_setup.py

# Option 1: Simple test (no ML dependencies)
python test_simple_server.py          # Terminal 1
cd frontend && npm run tauri dev      # Terminal 2

# Option 2: Full system (after installing requirements.txt)
python main.py                        # Terminal 1
cd frontend && npm run tauri dev      # Terminal 2
```

See [QUICKSTART.md](QUICKSTART.md) for detailed instructions.

## Communication Flow

```
React UI (TypeScript)
    ↓ Tauri invoke
Tauri Commands (Rust)  
    ↓ spawn Python subprocess
Python gRPC Clients
    ↓ gRPC calls
Chat Service (Port 50051)
    ↓ task dispatch
MCP Server (Port 50052)
    ↓ task assignment
Agents (Transcription, Vision, Generation)
```