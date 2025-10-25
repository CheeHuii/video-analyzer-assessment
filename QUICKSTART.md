# Quick Start: Running the Video Analyzer

This guide will get you up and running quickly with the wired frontend and backend.

## Prerequisites

- Python 3.8+
- Node.js 16+
- Rust (for Tauri)
- FFmpeg (in system PATH)

## Installation Steps

### 1. Backend Setup

```bash
# Install Python gRPC dependencies (minimum required)
pip install grpcio grpcio-tools protobuf

# For full functionality, install all dependencies:
# pip install -r requirements.txt
```

### 2. Frontend Setup

```bash
cd frontend
npm install
cd ..
```

## Running the System

### Option 1: Simple Chat Service (No ML dependencies)

Perfect for testing the wiring between frontend and backend.

**Terminal 1 - Start Simple Backend:**
```bash
python test_simple_server.py
```

You should see:
```
Starting simple chat server on port 50051...
gRPC server listening on 50051
```

**Terminal 2 - Start Frontend:**
```bash
cd frontend
npm run tauri dev
```

The desktop app will launch. You can now:
- Type messages in the chat
- See simulated agent responses
- View conversation history

### Option 2: Full System with AI Agents (Requires ML dependencies)

**First, download models:**
```bash
python model_download.py
```

**Then install all dependencies:**
```bash
pip install -r requirements.txt
```

**Start all services:**
```bash
python main.py
```

This starts:
- MCP Server (Agent Manager) on port 50052
- Chat Service on port 50051
- Transcription Agent
- Vision Agent
- Generation Agent

**Start Frontend:**
```bash
cd frontend
npm run tauri dev
```

Now you can:
- Upload videos
- Ask for transcriptions
- Request object detection
- Generate PDF/PowerPoint summaries

## Testing Backend Directly

### Test History Retrieval
```bash
python backend/grpc_client_get_history.py --addr localhost:50051 --conversation default
```

### Test Chat Streaming
```bash
python backend/grpc_client_stream.py --addr localhost:50051 --conversation test --text "Hello!"
```

## Architecture

```
Frontend (Tauri + React)
        ↓
Tauri Commands (Rust)
        ↓
Python gRPC Client Scripts
        ↓
Chat Service (Port 50051)
        ↓
MCP Server (Port 50052) ← Agents
```

## Component Status

✅ **Working:**
- Chat service and streaming
- Frontend-backend gRPC communication
- Message history storage (SQLite)
- Tauri file upload
- Basic UI components

🚧 **Requires ML Dependencies:**
- Video ingestion (needs ffmpeg)
- Transcription agent (needs faster-whisper)
- Vision agent (needs YOLO models)
- Generation agent (needs reportlab, python-pptx)
- LLM integration (needs transformers, torch)

## Troubleshooting

### "ModuleNotFoundError: No module named 'backend'"
Run scripts from repository root, not from subdirectories.

### "Connection refused" errors
Make sure the backend server is running before starting the frontend.

### "Cannot find python"
Ensure Python 3.8+ is in your PATH. On Windows, try `python3` instead of `python`.

### Tauri build issues
```bash
rustup update
cd frontend
rm -rf target
npm run tauri dev
```

## File Structure

```
/home/runner/work/video-analyzer-assessment/video-analyzer-assessment/
├── main.py                          # Start all services
├── test_simple_server.py            # Simple test server
├── backend/
│   ├── server.py                    # Simple chat service
│   ├── enhanced_server.py           # Chat with agent integration
│   ├── mcp_server.py                # Agent manager
│   ├── grpc_client_stream.py        # Client for Tauri
│   ├── grpc_client_get_history.py   # Client for Tauri
│   ├── db.py                        # SQLite storage
│   ├── ingest.py                    # Video processing
│   ├── agents/
│   │   ├── transcription_agent.py
│   │   ├── vision_agent.py
│   │   └── generation_agent.py
│   └── protos/                      # Generated gRPC code
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── grpcClient.ts            # gRPC wrapper
│   │   └── components/
│   │       ├── ChatWindow.tsx
│   │       ├── UploadPanel.tsx
│   │       └── HistoryPanel.tsx
│   └── src-tauri/
│       └── src/
│           └── commands.rs          # Tauri commands
└── protos/                          # Proto definitions
    ├── chat.proto
    └── agent_manager.proto
```

## Next Steps

1. **Test the simple setup first** to verify wiring works
2. **Install ML dependencies** for full functionality
3. **Download AI models** with `python model_download.py`
4. **Start full system** with `python main.py`

## Key Integration Points

### 1. Frontend → Backend
- `grpcClient.ts` calls Tauri commands
- Tauri commands spawn Python scripts
- Python scripts call gRPC services

### 2. Chat Service → Agents
- Chat service connects to MCP server
- MCP server manages agent lifecycle
- Agents register and receive tasks

### 3. Video Upload Flow
1. User selects video in UI
2. Frontend saves to local app data dir
3. Chat message triggers video ingestion
4. Backend extracts audio/frames
5. Tasks submitted to agents
6. Results streamed back to UI

## Support

For detailed setup and troubleshooting, see [SETUP_GUIDE.md](SETUP_GUIDE.md).
