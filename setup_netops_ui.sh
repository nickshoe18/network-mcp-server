#!/bin/bash
# Creates the complete netops-ui directory structure
# Run from: ~/hpe-networking-mcp
set -e

echo "Creating netops-ui structure..."

mkdir -p netops-ui/backend/src/routes
mkdir -p netops-ui/frontend/src/components
mkdir -p netops-ui/frontend/src/hooks
mkdir -p netops-ui/nginx

# ── Root files ────────────────────────────────────────────────────────────────

cat > netops-ui/.env.example << 'EOF'
# ──────────────────────────────────────────────────
#  NetOps UI — Root Environment
#  Copy to .env and fill in your values.
# ──────────────────────────────────────────────────

# Anthropic API key — platform.anthropic.com > API Keys
ANTHROPIC_API_KEY=your_anthropic_api_key_here

# Path to your hpe-networking-mcp secrets folder
SECRETS_DIR=/Users/nickshoemaker/hpe-networking-mcp/secrets
EOF

cat > netops-ui/docker-compose.yml << 'EOF'
services:

  hpe-mcp:
    image: hpe-networking-mcp:latest
    container_name: hpe-mcp
    volumes:
      - ${SECRETS_DIR:-./hpe-secrets}:/run/secrets:ro
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "python3 -c \"import urllib.request; urllib.request.urlopen('http://localhost:8000/health')\" 2>/dev/null || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 5
      start_period: 60s

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: netops-backend
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
      - MCP_SERVER_URL=http://hpe-mcp:8000/mcp
      - FRONTEND_URL=http://localhost:3000
      - PORT=3001
    depends_on:
      hpe-mcp:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: netops-frontend
    ports:
      - "3000:80"
    depends_on:
      - backend
    restart: unless-stopped

networks:
  default:
    name: netops-network
EOF

cat > netops-ui/README.md << 'EOF'
# HPE NetOps UI

Web-based chat interface for the HPE Networking MCP Server.
Connects Claude to Mist, Central, GreenLake, ClearPass, Axis, and UXI via a browser.

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY and SECRETS_DIR
docker compose up --build
```

Open http://localhost:3000
EOF

# ── Backend ───────────────────────────────────────────────────────────────────

cat > netops-ui/backend/package.json << 'EOF'
{
  "name": "netops-backend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js"
  },
  "dependencies": {
    "@anthropic-ai/sdk": "^0.24.0",
    "cors": "^2.8.5",
    "dotenv": "^16.4.5",
    "express": "^4.19.2",
    "express-rate-limit": "^7.3.1",
    "helmet": "^7.1.0"
  }
}
EOF

cat > netops-ui/backend/Dockerfile << 'EOF'
FROM node:20-slim
WORKDIR /app
COPY package.json ./
RUN npm install --production
COPY src/ ./src/
RUN useradd --create-home appuser
USER appuser
EXPOSE 3001
CMD ["node", "src/index.js"]
EOF

cat > netops-ui/backend/.env.example << 'EOF'
ANTHROPIC_API_KEY=your_anthropic_api_key_here
MCP_SERVER_URL=http://hpe-mcp:8000/mcp
FRONTEND_URL=http://localhost:3000
PORT=3001
EOF

cat > netops-ui/backend/src/index.js << 'EOF'
import "dotenv/config";
import express from "express";
import cors from "cors";
import helmet from "helmet";
import rateLimit from "express-rate-limit";
import { chatRouter } from "./routes/chat.js";
import { healthRouter } from "./routes/health.js";

const app = express();
const PORT = process.env.PORT || 3001;

app.use(helmet({ contentSecurityPolicy: false }));
app.use(cors({
  origin: process.env.FRONTEND_URL || "http://localhost:5173",
  methods: ["GET", "POST"],
  credentials: true,
}));
app.use(express.json());
app.use(rateLimit({ windowMs: 60 * 1000, max: 60,
  message: { error: "Too many requests." } }));

app.use("/api/chat", chatRouter);
app.use("/api/health", healthRouter);
app.get("/api/ping", (_, res) => res.json({ ok: true, ts: Date.now() }));

app.listen(PORT, () => {
  console.log(`NetOps backend running on port ${PORT}`);
  console.log(`MCP server: ${process.env.MCP_SERVER_URL}`);
});
EOF

cat > netops-ui/backend/src/routes/chat.js << 'EOF'
import { Router } from "express";
import Anthropic from "@anthropic-ai/sdk";

export const chatRouter = Router();
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MCP_URL = process.env.MCP_SERVER_URL || "http://hpe-mcp:8000/mcp";

chatRouter.post("/", async (req, res) => {
  const { messages } = req.body;
  if (!messages || !Array.isArray(messages))
    return res.status(400).json({ error: "messages array required" });

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const send = (event, data) =>
    res.write(`event: ${event}\ndata: ${JSON.stringify(data)}\n\n`);

  try {
    const stream = await client.beta.messages.stream({
      model: "claude-sonnet-4-20250514",
      max_tokens: 4096,
      system: `You are a network operations assistant connected to the HPE Networking MCP server.
You have access to tools for Juniper Mist, Aruba Central, HPE GreenLake, ClearPass, Aruba Axis, and UXI.
Be concise and precise. Format data as markdown tables where helpful.`,
      messages,
      mcp_servers: [{ type: "url", url: MCP_URL, name: "hpe-networking-mcp" }],
      betas: ["mcp-client-2025-04-04"],
    });

    stream.on("text", (text) => send("text", { text }));
    stream.on("message_start", () => send("start", { ts: Date.now() }));
    stream.on("content_block_start", (event) => {
      if (event.content_block?.type === "tool_use")
        send("tool_start", { name: event.content_block.name });
    });
    stream.on("content_block_stop", (event) => {
      if (event.content_block?.type === "tool_use")
        send("tool_end", { name: event.content_block.name });
    });

    const final = await stream.finalMessage();
    send("done", { usage: final.usage, stop_reason: final.stop_reason });

  } catch (err) {
    console.error("Chat error:", err.message);
    send("error", { message: err.message || "Request failed" });
  } finally {
    res.end();
  }
});
EOF

cat > netops-ui/backend/src/routes/health.js << 'EOF'
import { Router } from "express";
export const healthRouter = Router();
const MCP_URL = process.env.MCP_SERVER_URL || "http://hpe-mcp:8000/mcp";
const MCP_BASE = MCP_URL.replace("/mcp", "");

healthRouter.get("/", async (_, res) => {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const resp = await fetch(`${MCP_BASE}/health`, { signal: controller.signal });
    clearTimeout(timeout);
    if (!resp.ok) return res.status(502).json({ ok: false, error: `MCP returned ${resp.status}` });
    const data = await resp.json();
    res.json({ ok: true, ...data });
  } catch (err) {
    res.status(503).json({ ok: false,
      error: err.name === "AbortError" ? "MCP server timeout" : "MCP server unreachable" });
  }
});
EOF

# ── Frontend ──────────────────────────────────────────────────────────────────

cat > netops-ui/frontend/package.json << 'EOF'
{
  "name": "netops-frontend",
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "lucide-react": "^0.383.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-markdown": "^9.0.1"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "vite": "^5.3.1"
  }
}
EOF

cat > netops-ui/frontend/vite.config.js << 'EOF'
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": { target: "http://localhost:3001", changeOrigin: true } },
  },
});
EOF

cat > netops-ui/frontend/Dockerfile << 'EOF'
FROM node:20-slim AS builder
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
EOF

cat > netops-ui/frontend/nginx.conf << 'EOF'
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://backend:3001;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
EOF

cat > netops-ui/frontend/index.html << 'EOF'
<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>HPE Network Ops</title>
    <style>
      *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
      html, body, #root { height: 100%; }
      body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
             background: #0f1117; color: #e8eaf0; }
    </style>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
EOF

cat > netops-ui/frontend/src/main.jsx << 'EOF'
import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
createRoot(document.getElementById("root")).render(<App />);
EOF

cat > netops-ui/frontend/src/App.jsx << 'EOF'
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
EOF

cat > netops-ui/frontend/src/components/Sidebar.jsx << 'EOF'
import React from "react";

const QUICK_ACTIONS = [
  { label: "Network health overview",  prompt: "Run a full network health overview across all platforms" },
  { label: "Active alerts",            prompt: "Show all active alerts across Aruba Central and Juniper Mist" },
  { label: "Offline APs",             prompt: "List all offline APs in my Mist organisation" },
  { label: "ClearPass sessions",       prompt: "Show active ClearPass authentication sessions" },
  { label: "UXI sensor status",        prompt: "List all UXI sensors and their current test results" },
  { label: "GreenLake subscriptions",  prompt: "Show my HPE GreenLake workspace subscriptions" },
];

const STATUS_COLOR = { ok: "#1B8C6E", degraded: "#E08A00", unknown: "#888" };

export function Sidebar({ platforms, loading, onAction }) {
  return (
    <aside style={{ width: 240, flexShrink: 0, background: "#161820", borderRight: "1px solid #2a2d3a", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid #2a2d3a", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg,#1B4F8A,#1B8C6E)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, color: "#fff", fontWeight: 700 }}>H</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#e8eaf0" }}>HPE Network Ops</div>
          <div style={{ fontSize: 11, color: "#555" }}>AI Operations Centre</div>
        </div>
      </div>

      <div style={{ padding: "12px 12px 0" }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#555", letterSpacing: ".08em", marginBottom: 8, textTransform: "uppercase" }}>Platforms</div>
        {loading ? <div style={{ fontSize: 12, color: "#555", padding: "8px 0" }}>Connecting…</div> : platforms.map(p => (
          <div key={p.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 8px", borderRadius: 6, marginBottom: 2 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: STATUS_COLOR[p.status] ?? "#888", flexShrink: 0, boxShadow: p.status === "ok" ? `0 0 6px ${STATUS_COLOR.ok}80` : "none" }} />
              <span style={{ fontSize: 12, color: p.status === "ok" ? "#c8cad4" : "#666" }}>{p.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ padding: "12px", borderTop: "1px solid #2a2d3a", marginTop: "auto" }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#555", letterSpacing: ".08em", marginBottom: 8, textTransform: "uppercase" }}>Quick actions</div>
        {QUICK_ACTIONS.map(({ label, prompt }) => (
          <button key={label} onClick={() => onAction(prompt)}
            style={{ width: "100%", textAlign: "left", padding: "6px 8px", marginBottom: 3, background: "none", border: "1px solid #2a2d3a", borderRadius: 6, fontSize: 11, color: "#888", cursor: "pointer" }}
            onMouseEnter={e => { e.target.style.background = "#1e2030"; e.target.style.color = "#c8cad4"; }}
            onMouseLeave={e => { e.target.style.background = "none"; e.target.style.color = "#888"; }}>
            {label} ↗
          </button>
        ))}
      </div>
    </aside>
  );
}
EOF

cat > netops-ui/frontend/src/components/StatusBar.jsx << 'EOF'
import React from "react";
const STATUS_COLOR = { ok: "#1B8C6E", degraded: "#E08A00", unknown: "#888" };
export function StatusBar({ platforms, loading }) {
  const connected = platforms.filter(p => p.status === "ok").length;
  const total = platforms.length;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px", height: 44, background: "#161820", borderBottom: "1px solid #2a2d3a", flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: connected === total ? "#1B8C6E" : "#E08A00", boxShadow: `0 0 8px ${connected === total ? "#1B8C6E" : "#E08A00"}80` }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "#e8eaf0" }}>HPE Network Ops</span>
      </div>
      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
        {!loading && <span style={{ fontSize: 12, color: "#555" }}>{connected}/{total} platforms connected · 1,034 tools</span>}
        {platforms.map(p => (
          <div key={p.key} style={{ width: 6, height: 6, borderRadius: "50%", background: STATUS_COLOR[p.status] ?? "#888" }} title={p.label} />
        ))}
      </div>
    </div>
  );
}
EOF

cat > netops-ui/frontend/src/components/ChatPanel.jsx << 'EOF'
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
EOF

cat > netops-ui/frontend/src/hooks/useChat.js << 'EOF'
import { useState, useRef, useCallback } from "react";

export function useChat() {
  const [messages, setMessages]       = useState([]);
  const [streaming, setStreaming]     = useState(false);
  const [activeTools, setActiveTools] = useState([]);
  const abortRef = useRef(null);

  const send = useCallback(async (userText) => {
    if (streaming || !userText.trim()) return;
    const userMsg = { role: "user", content: userText, id: Date.now() };
    const history = [...messages, userMsg].map(({ role, content }) => ({ role, content }));
    setMessages(prev => [...prev, userMsg]);
    setStreaming(true);
    setActiveTools([]);

    const assistantId = Date.now() + 1;
    setMessages(prev => [...prev, { role: "assistant", content: "", id: assistantId, streaming: true }]);
    abortRef.current = new AbortController();

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ messages: history }),
        signal: abortRef.current.signal,
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let lastEvent = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop();

        for (const line of lines) {
          if (line.startsWith("event: ")) { lastEvent = line.slice(7).trim(); continue; }
          if (!line.startsWith("data: ")) continue;
          try {
            const data = JSON.parse(line.slice(6));
            if (lastEvent === "text" && data.text)
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: m.content + data.text } : m));
            if (lastEvent === "tool_start" && data.name)
              setActiveTools(prev => [...prev, data.name]);
            if (lastEvent === "tool_end" && data.name)
              setActiveTools(prev => prev.filter(n => n !== data.name));
            if (lastEvent === "done")
              setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, streaming: false } : m));
          } catch {}
        }
      }
    } catch (e) {
      if (e.name !== "AbortError")
        setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, content: "Error: " + e.message, streaming: false, error: true } : m));
    } finally {
      setStreaming(false);
      setActiveTools([]);
      setMessages(prev => prev.map(m => m.id === assistantId ? { ...m, streaming: false } : m));
    }
  }, [messages, streaming]);

  const stop  = () => abortRef.current?.abort();
  const clear = () => { setMessages([]); setStreaming(false); };

  return { messages, streaming, activeTools, send, stop, clear };
}
EOF

cat > netops-ui/frontend/src/hooks/usePlatformHealth.js << 'EOF'
import { useState, useEffect } from "react";

const PLATFORM_META = {
  mist:      { label: "Juniper Mist",   color: "#1B8C6E" },
  central:   { label: "Aruba Central",  color: "#185FA5" },
  greenlake: { label: "HPE GreenLake",  color: "#BA7517" },
  clearpass: { label: "ClearPass",      color: "#534AB7" },
  axis:      { label: "Aruba Axis",     color: "#993C1D" },
  uxi:       { label: "UXI",            color: "#3B6D11" },
};

export function usePlatformHealth(intervalMs = 30000) {
  const [health, setHealth]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  const fetch_ = async () => {
    try {
      const res  = await fetch("/api/health");
      const data = await res.json();
      setHealth(data);
      setError(null);
    } catch (e) {
      setError("Cannot reach backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetch_();
    const id = setInterval(fetch_, intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);

  const platforms = Object.entries(PLATFORM_META).map(([key, meta]) => ({
    key, ...meta,
    status:  health?.data?.platforms?.[key]?.status  ?? "unknown",
    message: health?.data?.platforms?.[key]?.message ?? "—",
  }));

  return { platforms, loading, error, refresh: fetch_ };
}
EOF

# ── Nginx VM config ───────────────────────────────────────────────────────────

cat > netops-ui/nginx/netops.conf << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name YOUR_DOMAIN;

    ssl_certificate     /etc/letsencrypt/live/YOUR_DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/YOUR_DOMAIN/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header Strict-Transport-Security "max-age=31536000" always;

    location / {
        proxy_pass http://localhost:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Connection '';
        proxy_buffering off;
        proxy_read_timeout 300s;
        chunked_transfer_encoding on;
    }
}
EOF

echo ""
echo "✅ netops-ui structure created successfully!"
echo ""
echo "Next steps:"
echo "  1. cd netops-ui"
echo "  2. cp .env.example .env"
echo "  3. Edit .env — add your ANTHROPIC_API_KEY"
echo "  4. docker compose up --build"
echo "  5. Open http://localhost:3000"
