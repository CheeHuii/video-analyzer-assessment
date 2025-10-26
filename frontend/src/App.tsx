// src/App.tsx
import React, { useEffect, useState } from "react";
import { listen } from "@tauri-apps/api/event";
import "./chat.css";
import ChatWindow from "./components/ChatWindow";
import UploadPanel from "./components/UploadPanel";
import HistoryPanel from "./components/HistoryPanel";
import ArtifactViewer from "./components/ArtifactViewer";
import { getHistory } from "./grpcClient";

export default function App() {
  const [convId, setConvId] = useState("default");
  const [history, setHistory] = useState<any[]>([]);
  const [videoId, setVideoId] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const resp = await getHistory(convId);
        const msgs = resp?.messages ?? [];
        if (msgs.length === 0) {
          const greet = {
            id: "greet-" + Date.now(),
            conversation_id: convId,
            sender: "agent",
            text: "Hi! I can help you transcribe, summarize, and detect objects in videos. Please upload a video to get started.",
            created_at: Date.now(),
            confidence: 0.0,
            needs_clarification: false,
            attachments: [],
            metadata_json: JSON.stringify({})
          };
          setHistory([greet]);
        } else {
          setHistory(msgs);
        }
        // derive latest video_id from agent message metadata
        let latest: string | null = null;
        for (let i = msgs.length - 1; i >= 0; i--) {
          const m = msgs[i];
          const metaStr = m?.metadata_json;
          if (!metaStr) continue;
          try {
            const meta = typeof metaStr === 'string' ? JSON.parse(metaStr) : metaStr;
            if (meta && meta.video_id) { latest = meta.video_id; break; }
          } catch {}
        }
        setVideoId(latest);
      } catch (e) {
        console.error("getHistory failed", e);
      }
    }
    load();
  }, [convId]);

  // Update videoId live when final streamed message arrives with metadata_json
  useEffect(() => {
    const setup = async () =>
      listen("stream_chunk", (e) => {
        try {
          const payload = JSON.parse(e.payload as string);
          if (payload && payload.message && payload.message.metadata_json) {
            const metaStr = payload.message.metadata_json;
            try {
              const meta = typeof metaStr === 'string' ? JSON.parse(metaStr) : metaStr;
              if (meta && meta.video_id) {
                setVideoId(meta.video_id);
              }
            } catch {}
          }
        } catch {}
      });
    let unlisten: any;
    setup().then((u:any)=>{ unlisten = u; });
    return () => { if (typeof unlisten === 'function') unlisten(); };
  }, []);

  return (
    <div className="app-container">
      <aside className="app-sidebar">
        <h2 className="text-lg font-bold mb-2">Conversations</h2>
        <HistoryPanel convId={convId} setConvId={setConvId} />
        <ArtifactViewer videoId={videoId || undefined} />
      </aside>

      <main className="app-main">
        <UploadPanel convId={convId} />
        <ChatWindow convId={convId} initialHistory={history} />
      </main>
    </div>
  );
}
