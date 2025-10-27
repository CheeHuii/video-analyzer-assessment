// src/components/ArtifactViewer.tsx
import React, { useEffect, useState } from "react";
import { invoke } from '@tauri-apps/api/core';

export default function ArtifactViewer({ videoId }: { videoId?: string }) {
  const [files, setFiles] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [videoIds, setVideoIds] = useState<string[]>([]);
  const [selectedId, setSelectedId] = useState<string | undefined>(videoId);

  async function load(videoId?: string) {
    setLoading(true);
    try {
      if (videoId) {
        const resp: string[] = await invoke('list_video_artifacts', { videoId });
        setFiles(resp || []);
      } else {
        // fallback to app attachments dir if no video selected
        const resp: string[] = await invoke('list_attachments');
        setFiles(resp || []);
      }
    } catch (e) {
      console.warn("artifact listing failed", e);
      setFiles([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    // initial fetch of available video ids
    (async () => {
      try {
        const ids: string[] = await invoke('list_video_ids');
        setVideoIds(ids || []);
        // sync selectedId: prefer prop, otherwise first id
        setSelectedId(prev => videoId ?? prev ?? ids?.[0]);
      } catch (e) {
        setVideoIds([]);
      }
    })();
  }, []);

  useEffect(() => {
    if (videoId) {
      (async () => {
        try {
          const ids: string[] = await invoke('list_video_ids');
          setVideoIds(ids || []);
        } catch (e) {
          // ignore
        }
      })();
      setSelectedId(videoId);
    }
  }, [videoId]);

  // reload when selectedId or prop videoId changes
  useEffect(() => {
    const idToUse = selectedId || videoId;
    load(idToUse);
  }, [videoId, selectedId]);

  return (
    <div className="mt-4">
      <div className="flex items-center gap-2 mb-2">
        <h3 className="font-semibold">Artifacts</h3>
        <div className="flex-1" />
        {videoIds.length > 0 && (
          <label className="text-sm text-gray-600">
            Video:
            <select
              className="ml-2 border rounded px-1 py-0.5 text-sm"
              value={selectedId || ''}
              onChange={(e)=> setSelectedId(e.target.value || undefined)}
            >
              <option value="">(none)</option>
              {videoIds.map(id => (
                <option key={id} value={id}>{id}</option>
              ))}
            </select>
          </label>
        )}
        <button
          className="ml-2 text-xs border px-2 py-0.5 rounded"
          onClick={async ()=>{
            try {
              const ids: string[] = await invoke('list_video_ids');
              setVideoIds(ids || []);
              if (!selectedId && ids && ids.length>0) setSelectedId(ids[0]);
            } catch (e) {}
          }}
        >Refresh</button>
      </div>
      {loading ? <div className="text-sm text-gray-500">Loading…</div> :
        files.length === 0 ? <div className="text-sm text-gray-500">No artifacts yet</div> :
        <ul>
          {files.map(f => {
            const name = f.split(/[\\/]/).pop() || f;
            return (
              <li key={f}>
                <a href="#" onClick={async(e)=>{ e.preventDefault(); await invoke('open_path', { path: f }); }}>{name}</a>
              </li>
            );
          })}
        </ul>
      }
    </div>
  );
}
