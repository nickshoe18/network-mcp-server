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

const JARVIS_STARTERS = [
  "Status update",
  "Any Marvis alerts?",
  "Where is device 10.103.10.10?",
  "Why can't a client on Guest get an IP?",
];

function ModeToggle({ mode, onModeChange, disabled, remote }) {
  if (remote) {
    return (
      <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "8px 20px", borderBottom: "1px solid #2a2d3a", background: "#161820" }}>
        <span style={{ padding: "5px 14px", fontSize: 12, borderRadius: 6, background: "#1B8C6E", color: "#fff" }}>Jarvis</span>
        <span style={{ fontSize: 11, color: "#555" }}>Remote session · read-only</span>
      </div>
    );
  }
  const btn = (m, label) => (
    <button onClick={() => onModeChange(m)} disabled={disabled}
      style={{ padding: "5px 14px", fontSize: 12, borderRadius: 6, border: "1px solid #2a2d3a", cursor: disabled ? "default" : "pointer",
        background: mode === m ? (m === "jarvis" ? "#1B8C6E" : "#1B4F8A") : "#1e2030", color: mode === m ? "#fff" : "#888" }}>
      {label}
    </button>
  );
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center", padding: "8px 20px", borderBottom: "1px solid #2a2d3a", background: "#161820" }}>
      {btn("assistant", "Assistant")}
      {btn("jarvis", "Jarvis")}
      <span style={{ fontSize: 11, color: "#555", marginLeft: 8 }}>
        {mode === "jarvis" ? "Level 1 engineer · read-only · uses runbooks" : "General network assistant"}
      </span>
    </div>
  );
}

export function ChatPanel({ messages, streaming, activeTools, onSend, mode = "assistant", onModeChange = () => {}, remote = false }) {
  const bottomRef = useRef(null);
  const [input, setInput] = useState("");
  const isJarvis = mode === "jarvis";

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, activeTools]);

  const submit = () => {
    const v = input.trim();
    if (!v || streaming) return;
    onSend(v);
    setInput("");
  };

  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <ModeToggle mode={mode} onModeChange={onModeChange} disabled={streaming} remote={remote} />
      <div style={{ flex: 1, overflowY: "auto", padding: "20px 24px" }}>
        {messages.length === 0 && !isJarvis && (
          <div style={{ textAlign: "center", marginTop: 80, color: "#444" }}>
            <div style={{ fontSize: 32, marginBottom: 12 }}>⬡</div>
            <div style={{ fontSize: 14, marginBottom: 6, color: "#666" }}>HPE Network Operations</div>
            <div style={{ fontSize: 12 }}>Ask anything about your network infrastructure</div>
          </div>
        )}
        {messages.length === 0 && isJarvis && (
          <div style={{ textAlign: "center", marginTop: 60, color: "#444" }}>
            <div style={{ fontSize: 32, marginBottom: 12, color: "#1B8C6E" }}>◈</div>
            <div style={{ fontSize: 14, marginBottom: 6, color: "#8ab" }}>Jarvis · Level 1 Network Engineer</div>
            <div style={{ fontSize: 12, marginBottom: 18 }}>Read-only triage for the lab network. Ask for a status update or describe a problem.</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center", maxWidth: 520, margin: "0 auto" }}>
              {JARVIS_STARTERS.map(s => (
                <button key={s} onClick={() => onSend(s)} disabled={streaming}
                  style={{ padding: "7px 12px", fontSize: 12, borderRadius: 16, border: "1px solid #2a2d3a", background: "#1e2030", color: "#9aa", cursor: "pointer" }}>{s}</button>
              ))}
            </div>
          </div>
        )}
        {messages.map(msg => <Message key={msg.id} msg={msg} activeTools={msg.streaming ? activeTools : []} />)}
        <div ref={bottomRef} />
      </div>

      <div style={{ padding: "12px 20px", borderTop: "1px solid #2a2d3a", background: "#161820" }}>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-end", background: "#1e2030", borderRadius: 10, border: "1px solid #2a2d3a", padding: "8px 12px" }}>
          <textarea value={input} onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }}
            placeholder={isJarvis ? "Ask Jarvis — e.g. status update, or describe a problem…" : "Ask about your network…"} rows={1}
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
