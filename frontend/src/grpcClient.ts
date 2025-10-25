import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

export type StreamChunkHandler = (payload: any) => void;

export async function saveUploadedFile(base64: string, filename: string) {
  const resp = await invoke('save_uploaded_file', { base64_data: base64, filename });
  return resp as { path: string };
}

export async function sendMessageAndStream(
  conversationId: string,
  sender: string,
  text: string,
  onChunk?: StreamChunkHandler
) {
  // start listening for stream events
  const unlisten = await listen('stream_chunk', event => {
    if (onChunk) {
      try {
        const data = JSON.parse(event.payload as string);
        onChunk(data);
      } catch (e) {
        console.error('invalid json stream event', e, event);
      }
    }
  });

  // call Tauri command to start streaming; it will emit events
  await invoke('send_message_and_stream', { conversation_id: conversationId, sender, text });

  // stop listening once done (optionally frontend can listen for a 'stream_done' event)
  await unlisten();
}

export async function getHistory(conversationId: string) {
  const resp = await invoke('get_history', { conversation_id: conversationId });
  return resp as any;
}

