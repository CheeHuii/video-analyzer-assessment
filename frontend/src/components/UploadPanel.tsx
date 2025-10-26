// src/components/UploadPanel.tsx
import React, { useState } from "react";
import { saveUploadedFile } from "../grpcClient";

type Props = {
  convId: string;
};

export default function UploadPanel({ convId: _ }: Props) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setProgress(10);

    // read file as base64
    const data = await file.arrayBuffer();
    // Convert to base64 in chunks to avoid stack overflow with large files
    const bytes = new Uint8Array(data);
    let binary = '';
    const chunkSize = 8192;
    for (let i = 0; i < bytes.length; i += chunkSize) {
      const chunk = bytes.subarray(i, Math.min(i + chunkSize, bytes.length));
      binary += String.fromCharCode(...chunk);
    }
    const b64 = btoa(binary);
    setProgress(30);

    try {
  await saveUploadedFile(b64, file.name);
  setProgress(90);
  // Do not auto-start analysis; user will prompt (e.g., "transcribe" / "summarize").
  // We intentionally avoid sending a chat message here to prevent auto-processing.
      setProgress(100);
    } catch (err) {
      console.error(err);
    } finally {
      setUploading(false);
      setTimeout(()=>setProgress(0), 700);
    }
  }

  return (
    <div className="mb-4">
      <label className="flex items-center gap-2">
        <input type="file" accept="video/mp4" onChange={onFileChange} />
      </label>
      {uploading && (
        <div className="mt-2">
          <div className="h-2 bg-gray-200 rounded">
            <div className="h-2 rounded bg-blue-500" style={{ width: `${progress}%` }} />
          </div>
          <div className="text-xs mt-1">Uploading... {progress}%</div>
        </div>
      )}
    </div>
  );
}
