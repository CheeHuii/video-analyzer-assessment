// src/components/ArtifactViewer.tsx
import React, { useEffect, useState } from "react";
import { invoke } from '@tauri-apps/api/core';

export default function ArtifactViewer() {
  const [files, setFiles] = useState<string[]>([]);

  useEffect(() => {
    async function load() {
      try {
        // call a Tauri command or read known attachments folder
        // quick approach: list attachments folder from app dir
        const resp: any = await invoke('list_attachments'); // implement in Rust
        setFiles(resp || []);
      } catch (e) {
        console.warn("no attachments listing", e);
      }
    }
    load();
  }, []);

  return (
    <div className="mt-4">
      <h3 className="font-semibold mb-2">Artifacts</h3>
      {files.length === 0 ? <div className="text-sm text-gray-500">No artifacts yet</div> :
        <ul>
          {files.map(f => <li key={f}><a href="#" onClick={async()=>{ await invoke('open_path', { path: f }); }}>{f.split('/').pop()}</a></li>)}
        </ul>
      }
    </div>
  );
}
