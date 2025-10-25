# video-analyzer-assessment
This is a project for test assessment

Runs fully offline using OpenVINO-optimized local models and MCP agents.

## Features (planned)
- Upload and process `.mp4` videos locally.
- Natural-language chat to query video content (transcribe, summarize, detect objects, etc.).
- PDF and PowerPoint generation.
- Persistent chat history.
- Fully local AI inference with modular agents.

## Repo Structure
- **frontend/** – React + Tauri chat UI
- **backend/** – Python MCP server and agents
- **proto/** – gRPC service definitions
- **docs/** – setup & architecture documentation
- **examples/** – sample input/output for testing
- **launcher/** – optional C# launcher for packaged backend

## Quick Start
```bash
# Window
install ffmpeg and install to system path
install protoc
download model to local with model_download.py

# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python main.py

# Frontend
cd ../frontend
cd src-tauri
cargo build
cd ..
npm run tauri dev


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
