// src/components/UploadPanel.tsx
import React, { useState } from "react";
import { saveUploadedFile, sendMessageAndStream } from "../grpcClient";

type Props = {
  convId: string;
  backendAddr: string;
};

export default function UploadPanel({ convId, backendAddr }: Props) {
  const [progress, setProgress] = useState(0);
  const [uploading, setUploading] = useState(false);

  async function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setProgress(10);

    // read file as base64
    const data = await file.arrayBuffer();
    const b64 = btoa(String.fromCharCode(...new Uint8Array(data)));
    setProgress(30);

    try {
      const resp = await saveUploadedFile(b64, file.name);
      setProgress(80);
      // instruct backend to process file via chat: e.g. "Transcribe <path>"
      const text = `Transcribe the video at ${resp.path}`;
      // stream responses directly to chat for immediate feedback
      await sendMessageAndStream(backendAddr, convId, "user", text, chunk => {
        // frontend will get stream events via grpcClient's onChunk
        // but here we don't pass handler; instead ChatWindow also listens to events globally
      });
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
