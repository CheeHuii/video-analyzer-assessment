
import { useEffect, useState } from "react";
import { sendMessageAndStream } from "../grpcClient";
import { listen } from "@tauri-apps/api/event";

type Props = {
  convId: string;
  initialHistory: any[];
  backendAddr: string;
};

export default function ChatWindow({ convId, initialHistory, backendAddr }: Props) {
  const [messages, setMessages] = useState<any[]>(initialHistory || []);
  const [input, setInput] = useState("");

  useEffect(() => {
    setMessages(initialHistory || []);
  }, [initialHistory]);

  useEffect(() => {
    // Listen for stream events from Tauri
    let unlistenPromise = listen("stream_chunk", (e) => {
      try {
        const payload = JSON.parse(e.payload as string);
        // payload shape depends on your proto -> prost mapping.
        // Here we handle partial_text and message final.
        if (payload.partial_text) {
          // append partial to a "temp" agent message or update last partial
          setMessages(prev => {
            const last = prev[prev.length - 1];
            if (last && last.__partial_agent) {
              last.text = (last.text || "") + payload.partial_text;
              return [...prev.slice(0, -1), { ...last }];
            } else {
              return [...prev, { id: "partial-"+Date.now(), sender: "agent", text: payload.partial_text, __partial_agent: true }];
            }
          });
        } else if (payload.message) {
          // final message object
          setMessages(prev => [...prev, payload.message]);
        }
      } catch (err) {
        console.error("stream parsing", err);
      }
    });

    return () => {
      // unlisten when component unmounts
      unlistenPromise.then(u => u && u());
    };
  }, []);

  async function onSend() {
    if (!input.trim()) return;
    // optimistic UI: push user message
    const userMsg = { id: "u-" + Date.now(), sender: "user", text: input };
    setMessages(prev => [...prev, userMsg]);
    const text = input;
    setInput("");
    // start server streaming via Tauri
    await sendMessageAndStream(backendAddr, convId, "user", text);
    // actual agent messages will arrive via stream_chunk events
  }

  return (
    <div className="flex-1 flex flex-col h-full">
      <div className="flex-1 overflow-auto p-2 border rounded">
        {messages.map((m, idx) => (
          <div key={m.id || idx} className={`mb-2 ${m.sender === 'user' ? 'text-right' : ''}`}>
            <div className={`inline-block p-2 rounded ${m.sender === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-100'}`}>
              {m.text}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-2 flex gap-2">
        <input className="flex-1 border p-2 rounded" value={input} onChange={e=>setInput(e.target.value)} />
        <button className="px-4 py-2 bg-blue-600 text-white rounded" onClick={onSend}>Send</button>
      </div>
    </div>
  );
}
