// src/App.tsx
import React, { useEffect, useState } from "react";
import ChatWindow from "./components/ChatWindow";
import UploadPanel from "./components/UploadPanel";
import HistoryPanel from "./components/HistoryPanel";
import ArtifactViewer from "./components/ArtifactViewer";
import { getHistory } from "./grpcClient";

export default function App() {
  const [convId, setConvId] = useState("default");
  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    async function load() {
      try {
        const resp = await getHistory(convId);
        setHistory(resp.messages ?? []);
      } catch (e) {
        console.error("getHistory failed", e);
      }
    }
    load();
  }, [convId]);

  return (
    <div className="h-screen flex">
      <aside className="w-80 border-r p-4">
        <h2 className="text-lg font-bold mb-2">Conversations</h2>
        <HistoryPanel convId={convId} setConvId={setConvId} />
        <ArtifactViewer />
      </aside>

      <main className="flex-1 p-4 flex flex-col">
        <UploadPanel convId={convId} />
        <ChatWindow convId={convId} initialHistory={history} />
      </main>
    </div>
  );
}
