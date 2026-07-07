import { Router } from "express";
import Anthropic from "@anthropic-ai/sdk";

export const chatRouter = Router();
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MCP_URL = process.env.MCP_SERVER_URL || "http://hpe-mcp:8000/mcp";

// ── MCP session management ────────────────────────────────────────────────────
async function initSession() {
  const resp = await fetch(MCP_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" },
    body: JSON.stringify({ jsonrpc: "2.0", id: 0, method: "initialize",
      params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "netops-ui", version: "1.0" } } }),
  });
  const sessionId = resp.headers.get("mcp-session-id") || resp.headers.get("x-mcp-session-id");
  await resp.text();
  return sessionId;
}

async function mcpCall(sessionId, method, params = {}) {
  const headers = { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" };
  if (sessionId) headers["mcp-session-id"] = sessionId;
  const resp = await fetch(MCP_URL, {
    method: "POST", headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: Math.floor(Math.random()*99999), method, params }),
  });
  const text = await resp.text();
  for (const line of text.split("\n").filter(l => l.startsWith("data:"))) {
    try {
      const d = JSON.parse(line.slice(5).trim());
      if (d.result !== undefined) return d.result;
    } catch {}
  }
  return null;
}

// ── Hardcoded tools Claude can call — all execute via MCP execute tool ────────
const TOOLS = [
  {
    name: "run_network_query",
    description: `Execute a network operations query against HPE networking platforms.
ALL SIX platforms are fully connected and available: Mist, Central, GreenLake, ClearPass, Axis, UXI.
NEVER say a platform is unavailable or not integrated - always try querying it first.
Use this for ANY query about network devices, sites, clients, alerts, config, health, etc.
The code parameter is Python that runs in the MCP execute sandbox using call_tool().

KEY PATTERNS:
- Central switches: await call_tool('central_invoke_tool', {'name': 'central_get_switches', 'params': {}})
  Switch serial is in field 'serialNumber' not 'serial'
- Switch port config (NEVER use show interface 1/1/X - blocked):
  1. vlans = await call_tool('central_invoke_tool', {'name': 'central_get_switch_vlans', 'params': {'serial_number': SERIAL}})
  2. poe = await call_tool('central_invoke_tool', {'name': 'central_get_switch_poe', 'params': {'serial_number': SERIAL}})
  3. show = await call_tool('central_invoke_tool', {'name': 'central_show_commands', 'params': {'serial_number': SERIAL, 'device_type': 'cx', 'commands': 'show running-config'}})
     Then parse show.get('data',{}).get('output',{}).get('results',[{}])[0].get('output','') for the interface section
- Central alerts require site_id: first call central_get_site_name_id_mapping
- Mist tools: await call_tool('mist_invoke_tool', {'name': 'mist_TOOLNAME', 'params': {...}})
- UXI: await call_tool('uxi_list_sensors', {}) or call_tool('uxi_get_sensor_status', {'sensor_id': ID})
- Skills: await call_tool('skills_list', {}) then call_tool('skills_load', {'name': SKILL})
- Always return structured data, not print statements`,
    input_schema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Python async code using await call_tool()" },
        description: { type: "string", description: "What this query does (for UI display)" }
      },
      required: ["code", "description"]
    }
  }
];

// ── POST /api/chat ─────────────────────────────────────────────────────────────
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
    const sessionId = await initSession();

    let currentMessages = [...messages];

    while (true) {
      const response = await client.messages.create({
        model: "claude-sonnet-4-5",
        max_tokens: 4096,
        system: `You are a network operations assistant with FULL ACCESS to all six HPE networking platforms:
1. Juniper Mist — wireless, APs, clients, SLE, alarms
2. Aruba Central — switches, APs, gateways, sites, alerts, config
3. HPE GreenLake — subscriptions, workspace, device inventory, users
4. Aruba ClearPass — auth sessions, policy services, endpoints, NADs, certificates
5. Aruba Axis — applications, connectors, tunnels, users, status
6. HPE UXI — sensors, synthetic tests, service test results

ALL SIX PLATFORMS ARE ALWAYS CONNECTED. Never tell the user a platform is unavailable or not integrated without first trying to query it.

You have ONE tool: run_network_query. Use it for EVERYTHING.

PLATFORM QUERY PATTERNS:
- ClearPass: await call_tool('clearpass_invoke_tool', {'name': 'clearpass_get_sessions', 'params': {}})
- GreenLake: await call_tool('greenlake_invoke_tool', {'name': 'greenlake_get_workspace', 'params': {}})
- Axis: await call_tool('axis_invoke_tool', {'name': 'axis_get_status', 'params': {}})
- Mist: await call_tool('mist_invoke_tool', {'name': 'mist_get_self', 'params': {}})
- Central: await call_tool('central_invoke_tool', {'name': 'central_get_sites', 'params': {}})
- UXI: await call_tool('uxi_list_sensors', {})

HEALTH CHECK: await call_tool('health', {}) — returns status of all 6 platforms at once.

SWITCH PORT QUERIES (NEVER use show interface 1/1/X - blocked by Central):
1. central_get_switches() — find serial in field 'serialNumber'
2. central_get_switch_vlans(serial_number=SERIAL) — filter for port
3. central_get_switch_poe(serial_number=SERIAL) — filter for port
4. central_show_commands(serial_number=SERIAL, device_type='cx', commands='show running-config') — parse interface section

Always format responses as markdown tables. Be concise and direct.`,
        messages: currentMessages,
        tools: TOOLS,
      });

      for (const block of response.content) {
        if (block.type === "text" && block.text) send("text", { text: block.text });
      }

      if (response.stop_reason !== "tool_use") break;

      const toolUseBlocks = response.content.filter(b => b.type === "tool_use");
      const toolResults = [];

      for (const toolUse of toolUseBlocks) {
        send("tool_start", { name: toolUse.input.description || toolUse.name });
        console.log("Executing:", toolUse.input.description || "query");

        try {
          const result = await mcpCall(sessionId, "tools/call", {
            name: "execute",
            arguments: { code: toolUse.input.code }
          });

          const resultText = result?.content?.[0]?.text || JSON.stringify(result);
          toolResults.push({
            type: "tool_result",
            tool_use_id: toolUse.id,
            content: [{ type: "text", text: resultText }],
          });
        } catch (e) {
          toolResults.push({
            type: "tool_result",
            tool_use_id: toolUse.id,
            content: [{ type: "text", text: "Error: " + e.message }],
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
