import { Router } from "express";
import Anthropic from "@anthropic-ai/sdk";

export const chatRouter = Router();
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MCP_URL = process.env.MCP_SERVER_URL || "http://hpe-mcp:8000/mcp";

// Parse SSE response lines into JSON-RPC result
function parseSSE(text) {
  const lines = text.split("\n").filter(l => l.startsWith("data:"));
  for (const line of lines) {
    try {
      const data = JSON.parse(line.slice(5).trim());
      if (data.result !== undefined) return data.result;
    } catch {}
  }
  return null;
}

// Initialize MCP session and return session ID
async function initSession() {
  const resp = await fetch(MCP_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Accept": "application/json, text/event-stream",
    },
    body: JSON.stringify({
      jsonrpc: "2.0", id: 0, method: "initialize",
      params: {
        protocolVersion: "2025-11-25",
        capabilities: {},
        clientInfo: { name: "netops-ui", version: "1.0.0" }
      }
    }),
  });
  const sessionId = resp.headers.get("mcp-session-id") || resp.headers.get("x-mcp-session-id");
  const text = await resp.text();
  return { sessionId, initResult: parseSSE(text) };
}

// Make authenticated MCP request with session ID
async function mcpRequest(sessionId, method, params = {}) {
  const headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/event-stream",
  };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  const resp = await fetch(MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: Math.floor(Math.random()*10000), method, params }),
  });
  const text = await resp.text();
  return parseSSE(text);
}

// Convert MCP tool to Anthropic format
function toAnthropicTool(mcpTool) {
  return {
    name: mcpTool.name,
    description: mcpTool.description || "",
    input_schema: mcpTool.inputSchema || { type: "object", properties: {} },
  };
}

chatRouter.post("/", async (req, res) => {
  const messages = req.body && req.body.messages;
  if (!messages || !Array.isArray(messages))
    return res.status(400).json({ error: "messages array required" });

  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const send = (event, data) =>
    res.write("event: " + event + "\ndata: " + JSON.stringify(data) + "\n\n");

  try {
    // Initialize MCP session
    const { sessionId } = await initSession();
    console.log("MCP session:", sessionId);

    // Get tools list
    const toolsResult = await mcpRequest(sessionId, "tools/list", {});
    const mcpTools = (toolsResult && toolsResult.tools) || [];
    const tools = mcpTools.slice(0, 64).map(toAnthropicTool);
    console.log("Loaded " + mcpTools.length + " tools, using " + tools.length);

    if (tools.length === 0) {
      send("text", { text: "Warning: Could not load tools from MCP server. Session: " + sessionId });
      send("done", { stop_reason: "error" });
      return;
    }

    let currentMessages = [...messages];

    // Agentic loop
    while (true) {
      const response = await client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 4096,
        system: "You are a network operations assistant connected to the HPE Networking MCP server. " +
          "You have access to tools for Juniper Mist, Aruba Central, HPE GreenLake, ClearPass, Aruba Axis, and UXI. " +
          "Be concise and precise. Format data as markdown tables where helpful. " +
          "Use the execute tool to run multi-step queries.",
        messages: currentMessages,
        tools,
      });

      for (const block of response.content) {
        if (block.type === "text" && block.text) send("text", { text: block.text });
      }

      if (response.stop_reason !== "tool_use") break;

      const toolUseBlocks = response.content.filter(b => b.type === "tool_use");
      const toolResults = [];

      for (const toolUse of toolUseBlocks) {
        send("tool_start", { name: toolUse.name });
        console.log("Calling: " + toolUse.name);
        try {
          const result = await mcpRequest(sessionId, "tools/call", { name: toolUse.name, arguments: toolUse.input || {} });
          toolResults.push({
            type: "tool_result",
            tool_use_id: toolUse.id,
            content: (result && result.content) || [{ type: "text", text: JSON.stringify(result) }],
          });
        } catch (e) {
          toolResults.push({
            type: "tool_result",
            tool_use_id: toolUse.id,
            content: [{ type: "text", text: "Tool error: " + e.message }],
            is_error: true,
          });
        }
        send("tool_end", { name: toolUse.name });
      }

      currentMessages = [
        ...currentMessages,
        { role: "assistant", content: response.content },
        { role: "user", content: toolResults },
      ];
    }

    send("done", { stop_reason: "end_turn" });

  } catch (err) {
    console.error("Chat error:", err.message);
    try { send("error", { message: err.message || "Request failed" }); } catch(e) {}
  } finally {
    try { res.end(); } catch(e) {}
  }
});
