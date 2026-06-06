import React from "react";
import { Sidebar } from "./components/Sidebar.jsx";
import { ChatPanel } from "./components/ChatPanel.jsx";
import { StatusBar } from "./components/StatusBar.jsx";
import { useChat } from "./hooks/useChat.js";
import { usePlatformHealth } from "./hooks/usePlatformHealth.js";

export default function App() {
  const { messages, streaming, activeTools, send } = useChat();
  const { platforms, loading } = usePlatformHealth(30000);

  return (
    <>
      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: #2a2d3a; border-radius: 2px; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:.3} }
        .md-body p { margin-bottom: 8px; }
        .md-body p:last-child { margin-bottom: 0; }
        .md-body ul, .md-body ol { padding-left: 18px; margin-bottom: 8px; }
        .md-body li { margin-bottom: 3px; }
        .md-body code { background: #12141c; border: 1px solid #2a2d3a; border-radius: 3px; padding: 1px 5px; font-size: 12px; font-family: monospace; }
        .md-body pre { background: #12141c; border: 1px solid #2a2d3a; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; overflow-x: auto; }
        .md-body pre code { background: none; border: none; padding: 0; }
        .md-body table { border-collapse: collapse; width: 100%; margin-bottom: 8px; font-size: 12px; }
        .md-body th { background: #12141c; padding: 5px 10px; border: 1px solid #2a2d3a; text-align: left; font-weight: 600; }
        .md-body td { padding: 5px 10px; border: 1px solid #2a2d3a; }
        .md-body h1,.md-body h2,.md-body h3 { margin-bottom: 8px; color: #e8eaf0; }
        .md-body strong { color: #e8eaf0; }
      `}</style>
      <div style={{ height: "100vh", display: "flex", flexDirection: "column", background: "#0f1117" }}>
        <StatusBar platforms={platforms} loading={loading} />
        <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
          <Sidebar platforms={platforms} loading={loading} onAction={send} />
          <main style={{ flex: 1, display: "flex", flexDirection: "column", background: "#12141c", overflow: "hidden" }}>
            <ChatPanel messages={messages} streaming={streaming} activeTools={activeTools} onSend={send} />
          </main>
        </div>
      </div>
    </>
  );
}
