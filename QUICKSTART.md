# Quick Start: Running the Video Analyzer

This guide will get you up and running quickly with the wired frontend and backend.

### System Requirements
- **Python 3.8+** (running with 3.11.9)
- **Node.js 16+** and npm (running with 10.9.3)
- **Rust** (for Tauri)
- **FFmpeg** (must be in system PATH)

## Installation Steps

### 1. Backend Setup

```bash
cd /path/to/video-analyzer-assessment

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt
```

### 2. Download AI Models (One-time setup)

```bash
cd /path/to/video-analyzer-assessment
python model_download.py
```

This will download:
- Whisper model for transcription
- YOLOv8 model for object detection
- TinyLlama model for text generation

### 3. Frontend Setup

```bash
cd /path/to/video-analyzer-assessment/frontend
npm install
```

## Running the System

**Terminal 1 - Start Simple Backend:**
```bash
python main.py
```

You should see:
```
INFO:main:============================================================
INFO:main:Starting Video Analyzer Backend
INFO:main:============================================================
INFO:main:Starting MCP server on [::]:50052
INFO:main:Starting Chat server on port 50051
...
[LLM] device set to cpu
INFO:sentence_transformers.SentenceTransformer:Load pretrained SentenceTransformer: backend/models/embedder/all-MiniLM-L6-v2
[RAG] initialized with model backend\models\llm\hf_llm
Enhanced gRPC Chat server listening on port 50051
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


## How to trigger each agent

After uploading a video (required), type one of these prompts in chat:

- Transcription:
        - "transcribe"
        - "get the transcript"

- Object detection (Vision):
        - "detect objects"
        - "is there any table?"

- Summaries and reports (Generation):
        - "summarize the video"
        - "create a pdf report"
        - "make a ppt/pptx slide deck"

Notes:
- If you haven't uploaded a video yet, the assistant will ask you to upload one first.
- The latest uploaded video is used when you don't attach a path.

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
