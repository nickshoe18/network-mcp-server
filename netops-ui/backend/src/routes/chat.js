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
        system: `You are a network operations assistant connected to the HPE Networking MCP server with 1,037 tools across Juniper Mist, Aruba Central, HPE GreenLake, ClearPass, Aruba Axis, and UXI.

CRITICAL RULES:
1. ALWAYS call skills_list first on any multi-step request. If a skill matches, load and follow it exactly.
2. Use execute for ALL multi-step queries. Inside execute, use <platform>_invoke_tool(name, params).
3. Before calling any tool inside execute, call <platform>_get_tool_schema to confirm exact parameter names.
4. Format responses as markdown tables where helpful. Be concise.

SWITCH PORT QUERIES (show port config, VLAN membership, PoE):
Central blocks show commands with interface names containing slashes (1/1/7 etc). Always use:
Step 1: central_get_switch_vlans(serial_number=SERIAL) then filter results for the port
Step 2: central_get_switch_poe(serial_number=SERIAL) then filter results for the port
Step 3: central_show_commands(serial_number=SERIAL, device_type='cx', commands='show running-config') then parse the interface section
NEVER use: show interface 1/1/X or show running-config interface 1/1/X — blocked by Central API.

CENTRAL PATTERNS:
- Switch serial field is serialNumber not serial
- Alerts always require site_id: central_get_alerts(site_id=ID)
- Show command device_type values: cx, aos-s, aps, gateways (lowercase)
- commands param is a single string not a list
- Get site IDs with central_get_site_name_id_mapping() first

MIST PATTERNS:
- All Mist tools go via mist_invoke_tool(name, params) inside execute
- Get org_id from mist_get_self() first
- Results are under data.results[]`,
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
