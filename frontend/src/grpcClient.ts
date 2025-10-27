import { invoke } from '@tauri-apps/api/core';
import { listen } from '@tauri-apps/api/event';

export type StreamChunkHandler = (payload: any) => void;

export async function saveUploadedFile(base64: string, filename: string) {
  const resp = await invoke('save_uploaded_file', { base64Data: base64, filename });
  // Backend returns a plain string path; normalize to { path }
  if (typeof resp === 'string') {
    return { path: resp } as { path: string };
  }
  // Fallback if shape already matches
  return resp as { path: string };
}

export async function sendMessageAndStream(
  conversationId: string,
  sender: string,
  text: string,
  onChunk?: StreamChunkHandler,
  attachments?: string[]
) {
  // start listening for stream events only if a handler is provided
  let unlisten: (() => void) | undefined;
  if (onChunk) {
    const u = await listen('stream_chunk', event => {
      try {
        const data = JSON.parse(event.payload as string);
        onChunk(data);
      } catch (e) {
        console.error('invalid json stream event', e, event);
      }
    });
    unlisten = u;
  }

  // call Tauri command to start streaming; it will emit events
  await invoke('send_message_and_stream', { conversationId, sender, text, attachments });

  if (unlisten) {
    unlisten();
  }
}

export async function getHistory(conversationId: string) {
  const resp = await invoke('get_history', { conversationId });
  if (typeof resp === 'string') {
    try { return JSON.parse(resp as string); } catch { return { messages: [] }; }
  }
  return resp as any;
}

