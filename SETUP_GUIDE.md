# Complete Setup Guide: Wiring Frontend and Backend Together

This guide provides step-by-step instructions to run the complete Video Analyzer system with frontend and backend fully integrated.

## Prerequisites

### System Requirements
- **Python 3.8+**
- **Node.js 16+** and npm
- **Rust** (for Tauri)
- **FFmpeg** (must be in system PATH)
- **Operating System**: Windows, macOS, or Linux

### Install FFmpeg
```bash
# Windows (using chocolatey)
choco install ffmpeg

# macOS (using homebrew)
brew install ffmpeg

# Linux (Ubuntu/Debian)
sudo apt-get install ffmpeg

# Verify installation
ffmpeg -version
```

## Step 1: Clone and Navigate to Repository

```bash
cd /path/to/video-analyzer-assessment
```

## Step 2: Backend Setup

### 2.1 Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate

# On macOS/Linux:
source venv/bin/activate
```

### 2.2 Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2.3 Download AI Models (One-time setup)

```bash
python model_download.py
```

This will download:
- Whisper model for transcription
- YOLOv8 model for object detection
- TinyLlama model for text generation

**Note**: Model downloads may take 10-30 minutes depending on your internet speed.

### 2.4 Verify Backend Structure

Ensure these directories exist:
```bash
mkdir -p data/videos
mkdir -p data/attachments
mkdir -p backend/models
```

## Step 3: Frontend Setup

### 3.1 Install Node.js Dependencies

```bash
cd frontend
npm install
```

### 3.2 Install Tauri CLI (if not already installed)

```bash
npm install -g @tauri-apps/cli
```

### 3.3 Setup Rust for Tauri

If you haven't installed Rust:

```bash
# Install Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh

# Or on Windows, download from: https://rustup.rs/
```

### 3.4 Return to Root Directory

```bash
cd ..
```

## Step 4: Running the Complete System

### Option A: Run Backend and Frontend Separately (Recommended for Development)

#### Terminal 1 - Start Backend Services
```bash
# Make sure virtual environment is activated
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Start all backend services (MCP Server, Chat Service, and Agents)
python main.py
```

You should see output like:
```
============================================================
Starting Video Analyzer Backend
============================================================
INFO - Starting MCP server on [::]:50052
INFO - Starting Chat server on port 50051
INFO - Starting agents...
INFO - Registered with server: <agent_id> ok=True
============================================================
All services started successfully!
MCP Server (Agent Manager): [::]:50052
Chat Service: [::]:50051
Agents: transcription, vision, generation
============================================================
```

#### Terminal 2 - Start Frontend
```bash
cd frontend
npm run tauri dev
```

The Tauri desktop application should launch automatically.

### Option B: Run with npm scripts (Alternative)

You can also add scripts to package.json for easier management.

## Step 5: Using the Application

### 5.1 First Time Launch

1. The desktop app will open showing a chat interface
2. You'll see:
   - Left sidebar: Conversation history and artifacts
   - Main area: Upload panel and chat window

### 5.2 Upload and Analyze a Video

1. **Upload a video**:
   - Click the upload button in the UploadPanel
   - Select an MP4, AVI, or MOV file
   - Wait for upload to complete

2. **Ask questions**:
   - Type in the chat: "Transcribe this video"
   - Or: "What objects can you detect?"
   - Or: "Generate a summary PDF"

3. **View results**:
   - Transcription results appear in the chat
   - Generated PDFs/PPTXs appear in the artifacts viewer
   - Click to open them with your default application

### 5.3 Example Queries

```
User: "Transcribe this video"
→ Triggers transcription agent, extracts speech-to-text

User: "What objects are in the video?"
→ Triggers vision agent, detects objects in frames

User: "Create a PowerPoint summary"
→ Triggers generation agent, creates PPTX from transcript

User: "Analyze this video completely"
→ Triggers all three agents in sequence
```

## Step 6: Architecture Overview

### Backend Components (Port Assignments)

1. **MCP Server (Agent Manager)** - Port 50052
   - Manages agent registration and lifecycle
   - Routes tasks to appropriate agents
   - Tracks task progress

2. **Chat Service** - Port 50051
   - Handles user chat interactions
   - Parses user intent
   - Communicates with MCP to dispatch tasks
   - Stores chat history in SQLite

3. **Agents** (connect to MCP Server)
   - **Transcription Agent**: Uses Whisper for speech-to-text
   - **Vision Agent**: Uses YOLOv8 for object detection
   - **Generation Agent**: Creates PDF/PPTX summaries

### Frontend Components

1. **Tauri App** (Rust)
   - Native desktop wrapper
   - Provides file system access
   - Executes Python gRPC client scripts

2. **React UI**
   - Chat interface
   - Video upload component
   - History and artifacts viewer

3. **gRPC Client Scripts** (Python)
   - `backend/grpc_client_stream.py`: Streams chat responses
   - `backend/grpc_client_get_history.py`: Fetches history

### Communication Flow

```
┌─────────────────┐
│  React UI       │
│  (TypeScript)   │
└────────┬────────┘
         │ Tauri invoke()
         ▼
┌─────────────────┐
│  Tauri Commands │
│  (Rust)         │
└────────┬────────┘
         │ spawn Python
         ▼
┌─────────────────┐      ┌──────────────┐
│  gRPC Clients   │─────▶│ Chat Service │
│  (Python)       │◀─────│ (Port 50051) │
└─────────────────┘      └──────┬───────┘
                                │
                                ▼
                         ┌──────────────┐
                         │  MCP Server  │
                         │ (Port 50052) │
                         └──────┬───────┘
                                │
                ┌───────────────┼───────────────┐
                ▼               ▼               ▼
         ┌──────────┐    ┌──────────┐   ┌──────────┐
         │Transcript│    │  Vision  │   │Generation│
         │  Agent   │    │  Agent   │   │  Agent   │
         └──────────┘    └──────────┘   └──────────┘
```

## Step 7: Troubleshooting

### Backend Issues

**Problem**: `ModuleNotFoundError: No module named 'backend'`
```bash
# Solution: Make sure you're running from the repository root
cd /path/to/video-analyzer-assessment
python main.py
```

**Problem**: `grpc.RpcError: failed to connect to all addresses`
```bash
# Solution: Make sure MCP server started before agents
# Check logs for "MCP server started on [::]:50052"
```

**Problem**: FFmpeg not found
```bash
# Solution: Install FFmpeg and add to PATH
# Verify: ffmpeg -version
```

**Problem**: Models not found
```bash
# Solution: Run model download script
python model_download.py
```

### Frontend Issues

**Problem**: `Cannot connect to backend`
```bash
# Solution 1: Verify backend is running
# Solution 2: Check backend address in frontend/src/App.tsx
# Should be: http://[::1]:50051 or http://localhost:50051
```

**Problem**: Tauri build fails
```bash
# Solution: Update Rust
rustup update

# Clean and rebuild
cd frontend
rm -rf target
npm run tauri build
```

**Problem**: Python script not found
```bash
# Solution: Make sure you're running from repository root
# Tauri commands expect to find backend/ directory
```

### Performance Issues

**Problem**: Slow inference
```bash
# This is expected with CPU-only inference
# Solutions:
# 1. Use smaller models (already configured)
# 2. If you have Intel GPU, OpenVINO should auto-detect
# 3. Reduce video resolution during ingest
```

## Step 8: Development Tips

### Hot Reload

- **Backend**: Restart `python main.py` after code changes
- **Frontend**: Vite hot reload works automatically with `npm run tauri dev`

### Debugging

#### Backend Logs
```bash
# All backend components log to stdout
# Check for ERROR or WARNING messages
```

#### Frontend Logs
- Open DevTools in the Tauri app (F12)
- Check Console tab for JavaScript errors
- Check Network tab for gRPC issues

#### gRPC Debugging
```bash
# Test gRPC directly
python backend/grpc_client_get_history.py --addr localhost:50051 --conversation default

python backend/grpc_client_stream.py --addr localhost:50051 --conversation default --text "Hello"
```

### Database

Chat history is stored in SQLite:
```bash
# Location: data/chat.db
# View contents:
sqlite3 data/chat.db
> SELECT * FROM messages;
```

## Step 9: Building for Production

### Backend Distribution

Package backend as an executable (optional):
```bash
pip install pyinstaller
pyinstaller --onefile main.py
```

### Frontend Distribution

Build Tauri app:
```bash
cd frontend
npm run tauri build
```

Installers will be in: `frontend/src-tauri/target/release/bundle/`

## Step 10: Next Steps and Enhancements

### Immediate Improvements
- [ ] Add progress bars for video processing
- [ ] Implement conversation management (create/delete)
- [ ] Add error notifications in UI
- [ ] Improve LLM integration for smarter routing

### Future Features
- [ ] Support for more video formats
- [ ] Real-time video analysis during upload
- [ ] Multi-language support for transcription
- [ ] Custom agent plugins
- [ ] Cloud sync (optional)

## Quick Reference: Common Commands

```bash
# Start everything
python main.py                    # Terminal 1: Backend
cd frontend && npm run tauri dev  # Terminal 2: Frontend

# Test backend only
python backend/enhanced_server.py
python backend/mcp_server.py

# Test individual agents
python -m backend.agents.transcription_agent

# View chat history
python backend/grpc_client_get_history.py --addr localhost:50051 --conversation default

# Send test message
python backend/grpc_client_stream.py --addr localhost:50051 --conversation default --text "Test message"

# Ingest a video manually
python backend/ingest.py path/to/video.mp4

# Generate protos (if modified)
cd frontend
npm run proto:gen
```

## Support and Resources

- **Issue Tracker**: Check repository issues
- **Documentation**: See `Note.md` for additional details
- **Models**: All inference runs locally, no internet required after setup

---

**Note**: This system runs entirely offline after initial setup. No cloud connectivity is required for AI inference.
