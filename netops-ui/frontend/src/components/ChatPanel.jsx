import React, { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";

function ToolBadge({ name }) {
  const short = name.replace(/^(mist_|central_|greenlake_|clearpass_|axis_|uxi_)/, "");
  return (
    <div style={{ display: "inline-flex", alignItems: "center", gap: 5, padding: "3px 8px", borderRadius: 4, background: "#1e2030", border: "1px solid #2a2d3a", fontSize: 11, color: "#666", margin: "2px 0" }}>
      <span style={{ width: 6, height: 6, borderRadius: "50%", background: "#1B8C6E", animation: "pulse 1.2s infinite" }} />
      {short}
    </div>
  );
}

function Message({ msg, activeTools }) {
  const isUser = msg.role === "user";
  return (
    <div style={{ display: "flex", justifyContent: isUser ? "flex-end" : "flex-start", marginBottom: 16 }}>
      <div style={{ maxWidth: "78%" }}>
        {!isUser && activeTools.length > 0 && msg.streaming && (
          <div style={{ marginBottom: 6, display: "flex", flexWrap: "wrap", gap: 4 }}>
            {activeTools.map(t => <ToolBadge key={t} name={t} />)}
          </div>
        )}
        <div style={{ padding: "10px 14px", borderRadius: isUser ? "14px 14px 4px 14px" : "14px 14px 14px 4px", background: isUser ? "#1B4F8A" : "#1e2030", border: isUser ? "none" : "1px solid #2a2d3a", fontSize: 13, lineHeight: 1.6, color: isUser ? "#fff" : "#c8cad0" }}>
          {isUser ? <span>{msg.content}</span> : (
            <div className="md-body">
              <ReactMarkdown>{msg.content || (msg.streaming ? "▋" : "")}</ReactMarkdown>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export function ChatPanel({ messages, streaming, activeTools, onSend }) {
  const bottomRef = useRef(null);
  const [input, setInput] = useState("");

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, activeTools]);

  const submit = () => {
    const v = input.trim();
    if (!v || streaming) return;
    onSend(v);
    setInput("");
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {messages.length === 0 && (
          <div style={{ textAlign: "center", marginTop: 80, color: "#444" }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>⬡</div>
            <div style={{ fontSize: 14, marginBottom: 6, color: "#666" }}>HPE Network Operations</div>
            <div style={{ fontSize: 12 }}>Ask anything about your network infrastructure</div>
          </div>
        )}
        {messages.map(msg => <Message key={msg.id} msg={msg} activeTools={msg.streaming ? activeTools : []} />)}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: "12px 20px", borderTop: "1px solid #2a2d3a", background: "#161820" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", background: "#1e2030", borderRadius: 10, border: "1px solid #2a2d3a", padding: "8px 12px" }}>
          <textarea value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder="Ask about your network…" rows={1}
            style={{ flex: 1, background: "none", border: "none", outline: "none", color: "#e8eaf0", fontSize: 13, resize: "none", fontFamily: "inherit", lineHeight: 1.5 }} />
          <button onClick={submit} disabled={!input.trim() || streaming}
            style={{ width: 30, height: 30, borderRadius: 6, background: input.trim() && !streaming ? "#1B4F8A" : "#2a2d3a", border: "none", cursor: input.trim() && !streaming ? "pointer" : "default", color: "#fff", fontSize: 14, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
            {streaming ? "◼" : "↑"}
          </button>
        </div>
        <div style={{ fontSize: 11, color: "#444", marginTop: 6, textAlign: "center" }}>Enter to send · Shift+Enter for new line</div>
      </div>
    </div>
  );
}
