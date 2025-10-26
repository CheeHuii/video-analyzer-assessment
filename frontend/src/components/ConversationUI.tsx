import React, { useEffect, useRef, useState } from "react";

// Simple conversation UI component (TailwindCSS)
// Default export a React component. Usage: <ConversationUI onSend={(text, files)=>...} />

export type Message = {
  id: string;
  author: "me" | "bot" | string;
  text?: string;
  timestamp?: string; // ISO string
  status?: "sending" | "sent" | "failed";
  files?: { name: string; url?: string; size?: number }[];
};

export default function ConversationUI({
  onSend,
  initialMessages = [],
}: {
  onSend?: (text: string, files?: File[]) => Promise<void> | void;
  initialMessages?: Message[];
}) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  const [files, setFiles] = useState<File[]>([]);
  const [showScrollToBottom, setShowScrollToBottom] = useState(false);
  const listRef = useRef<HTMLDivElement | null>(null);

  // auto-scroll when new message arrives
  useEffect(() => {
    if (!listRef.current) return;
    const el = listRef.current;
    // if user scrolled near bottom, auto scroll, otherwise show button
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 150;
    if (nearBottom) {
      el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
      setShowScrollToBottom(false);
    } else {
      setShowScrollToBottom(true);
    }
  }, [messages]);

  // helpers
  const addLocalMessage = (text: string, f?: File[]) => {
    const m: Message = {
      id: String(Date.now()) + Math.random().toString(36).slice(2, 8),
      author: "me",
      text,
      timestamp: new Date().toISOString(),
      status: "sending",
      files: f?.map((ff) => ({ name: ff.name, size: ff.size })),
    };
    setMessages((s) => [...s, m]);
    return m;
  };

  const updateMessageStatus = (id: string, patch: Partial<Message>) => {
    setMessages((s) => s.map((m) => (m.id === id ? { ...m, ...patch } : m)));
  };

  async function handleSend() {
    const txt = value.trim();
    if (!txt && files.length === 0) return;
    setSending(true);
    const local = addLocalMessage(txt, files.length ? files : undefined);
    setValue("");
    setFiles([]);

    try {
      if (onSend) {
        // allow parent to return a promise for streaming or acknowledgement
        await onSend(txt, files.length ? files : undefined);
      } else {
        // no backend: echo bot response as placeholder
        await fakeBotReply(local.id, txt);
      }
      updateMessageStatus(local.id, { status: "sent" });
    } catch (e) {
      updateMessageStatus(local.id, { status: "failed" });
      console.error("send failed", e);
    } finally {
      setSending(false);
    }
  }

  // example fallback bot reply (simulate streaming/typing)
  async function fakeBotReply(replyToId: string, txt: string) {
    const botId = "bot-" + Date.now();
    const botMessage: Message = {
      id: botId,
      author: "bot",
      text: "",
      timestamp: new Date().toISOString(),
      status: "sending",
    };
    setMessages((s) => [...s, botMessage]);

    // simulate streaming by gradually appending characters
    const replyText = "Got it — you said: " + (txt || "(something)");
    for (let i = 0; i < replyText.length; i++) {
      await new Promise((r) => setTimeout(r, 12 + Math.random() * 40));
      setMessages((s) =>
        s.map((m) => (m.id === botId ? { ...m, text: (m.text || "") + replyText[i] } : m))
      );
    }
    updateMessageStatus(botId, { status: "sent" });
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function onFileChange(ev: React.ChangeEvent<HTMLInputElement>) {
    const files = ev.target.files;
    if (!files) return;
    const arr = Array.from(files).slice(0, 3); // limit to 3 files by default
    setFiles((s) => [...s, ...arr]);
    // clear the input to allow same file to be chosen later
    ev.currentTarget.value = "";
  }

  function removeFile(idx: number) {
    setFiles((s) => s.filter((_, i) => i !== idx));
  }

  function renderMessage(m: Message) {
    const isMe = m.author === "me";
    const time = m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : "";
    return (
      <div key={m.id} className={`flex items-end gap-3 ${isMe ? "justify-end" : "justify-start"}`}>
        {!isMe && (
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-sm text-gray-700">B</div>
        )}

        <div className={`max-w-[70%] md:max-w-[60%]`}> 
          <div
            className={`px-4 py-2 rounded-2xl break-words leading-relaxed ${
              isMe ? "bg-blue-600 text-white rounded-br-none" : "bg-white border border-gray-200 text-gray-900 rounded-bl-none"
            }`}
          >
            {m.text}
          </div>

          {m.files && m.files.length > 0 && (
            <div className={`flex gap-2 mt-2 ${isMe ? "justify-end" : "justify-start"}`}>
              {m.files.map((f, i) => (
                <div key={i} className="text-xs border rounded p-2 bg-gray-50">
                  <div className="font-medium">{f.name}</div>
                  {f.size != null && <div className="text-[10px] text-gray-500">{Math.round((f.size || 0) / 1024)} KB</div>}
                </div>
              ))}
            </div>
          )}

          <div className="text-[11px] text-gray-400 mt-1 flex items-center gap-2">
            <span>{time}</span>
            {m.status === "sending" && <span>• sending…</span>}
            {m.status === "failed" && <span className="text-red-500">• failed</span>}
          </div>
        </div>

        {isMe && <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center text-sm text-white">Me</div>}
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col bg-neutral-50 border rounded-lg shadow-sm">
      {/* Header */}
      <div className="px-4 py-3 border-b bg-white flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white font-semibold">AI</div>
          <div>
            <div className="font-semibold">Video Analyzer</div>
            <div className="text-xs text-gray-500">Ready to chat</div>
          </div>
        </div>
        <div className="text-xs text-gray-500">Online</div>
      </div>

      {/* Messages */}
      <div ref={listRef} className="flex-1 overflow-auto p-4 space-y-4" aria-live="polite">
        {messages.length === 0 && (
          <div className="text-center text-sm text-gray-400 mt-12">No messages yet — ask about your video</div>
        )}

        <div className="flex flex-col gap-4">
          {messages.map((m) => renderMessage(m))}
        </div>
      </div>

      {/* Scroll to bottom button */}
      {showScrollToBottom && (
        <button
          onClick={() => listRef.current?.scrollTo({ top: listRef.current.scrollHeight, behavior: "smooth" })}
          className="absolute bottom-28 right-6 bg-white border px-3 py-1 rounded-full shadow"
          aria-label="Scroll to latest message"
        >
          ↓ Latest
        </button>
      )}

      {/* Composer */}
      <div className="px-4 py-3 border-t bg-white">
        {/* file preview */}
        {files.length > 0 && (
          <div className="mb-2 flex gap-2">
            {files.map((f, i) => (
              <div key={i} className="border rounded p-2 text-xs flex items-center gap-2">
                <div className="w-6 h-6 bg-gray-100 rounded flex items-center justify-center">📎</div>
                <div className="min-w-0">
                  <div className="truncate max-w-[120px]">{f.name}</div>
                  <div className="text-[10px] text-gray-500">{Math.round(f.size / 1024)} KB</div>
                </div>
                <button onClick={() => removeFile(i)} className="text-red-500 text-xs">Remove</button>
              </div>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <label className="flex items-center gap-2 px-3 py-2 border rounded cursor-pointer bg-white">
            <input type="file" multiple className="hidden" onChange={onFileChange} />
            <span className="text-sm">📎</span>
            <span className="text-sm text-gray-600">Attach</span>
          </label>

          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your message — Enter to send, Shift+Enter for newline"
            className="flex-1 resize-none rounded-md px-3 py-2 border focus:outline-none focus:ring-2 focus:ring-blue-300 text-sm"
            rows={1}
            aria-label="Message input"
          />

          <button
            onClick={handleSend}
            disabled={sending}
            className={`px-4 py-2 rounded-md ${sending ? "bg-gray-300 text-gray-600" : "bg-blue-600 text-white"}`}
            aria-label="Send message"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
