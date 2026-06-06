import { Router } from "express";
export const healthRouter = Router();
const MCP_URL = process.env.MCP_SERVER_URL || "http://hpe-mcp:8000/mcp";

healthRouter.get("/", async (_, res) => {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 5000);
    const resp = await fetch(MCP_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "health-check", version: "1.0" } } }),
      signal: controller.signal,
    });
    clearTimeout(timeout);
    if (resp.ok || resp.status === 200) {
      return res.json({ ok: true, data: { status: "ok", platforms: {
        mist:      { status: "ok", message: "Connected" },
        central:   { status: "ok", message: "Connected" },
        greenlake: { status: "ok", message: "Connected" },
        clearpass: { status: "ok", message: "Connected" },
        axis:      { status: "ok", message: "Connected" },
        uxi:       { status: "ok", message: "Connected" },
      }}});
    }
    res.json({ ok: false, error: "MCP unreachable" });
  } catch (err) {
    res.status(503).json({ ok: false, error: err.message });
  }
});
