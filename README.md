# video-analyzer-assessment
This is a project for test assessment

Runs fully offline using OpenVINO-optimized local models and MCP agents.

## 🎯 Quick Start

**NEW**: Frontend and backend are now fully wired! See [QUICKSTART.md](QUICKSTART.md) for immediate setup.

### Minimal Setup (Test Wiring Only)
```bash
# Install minimal dependencies
pip install grpcio grpcio-tools protobuf

# Start backend
python test_simple_server.py

# In another terminal, start frontend
cd frontend && npm install && npm run tauri dev
```

### Full Setup (With AI Features)
```bash
# Install all dependencies
pip install -r requirements.txt

# Download AI models
python model_download.py

# Start all services (MCP + Chat + Agents)
python main.py

# In another terminal, start frontend
cd frontend && npm run tauri dev
```

## ✅ What's Working

- ✅ Frontend-Backend gRPC communication
- ✅ Chat interface with streaming responses
- ✅ Message history persistence
- ✅ File upload via Tauri
- ✅ Agent management infrastructure
- ✅ Video ingestion pipeline
- ✅ All three agents (transcription, vision, generation)

## 📚 Documentation

- **[QUICKSTART.md](QUICKSTART.md)** - Fast setup and testing
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Comprehensive guide with architecture details
- **[check_setup.py](check_setup.py)** - Verify your environment

## Features (planned)
- Upload and process `.mp4` videos locally.
- Natural-language chat to query video content (transcribe, summarize, detect objects, etc.).
- PDF and PowerPoint generation.
- Persistent chat history.
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


# File structure (expected)
genai-video-analyzer/
├── README.md
├── .gitignore
├── LICENSE
│
├── backend/
│   ├── main.py                 # entry point (starts MCP + agents)
│   ├── requirements.txt
│   ├── mcp_server/
│   │   ├── __init__.py
│   │   └── server.py           # main gRPC server
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base_agent.py
│   │   ├── transcription_agent.py
│   │   ├── vision_agent.py
│   │   └── generation_agent.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   └── video_ingest.py
│   ├── storage/
│   │   ├── __init__.py
│   │   └── chat_store.py       # persistent chat history (SQLite)
│   └── utils/
│       └── __init__.py
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx
│   │   │   ├── UploadPanel.tsx
│   │   │   └── HistoryPanel.tsx
│   │   └── main.tsx
│   ├── package.json
│   ├── tauri.conf.json
│   └── tsconfig.json
│
├── proto/
│   ├── chat.proto
│   ├── agent.proto
│   └── mcp.proto
│
├── examples/
│   ├── sample_video.mp4
│   ├── expected_output.pdf
│   └── expected_output.pptx
│
├── docs/
│   ├── setup.md
│   ├── architecture.md
│   └── limitations_and_next_steps.md
│
└── launcher/
    ├── Launcher.cs
    └── Launcher.sln
