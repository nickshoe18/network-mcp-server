import { Router } from "express";
import Anthropic from "@anthropic-ai/sdk";
import { JARVIS_SYSTEM, JARVIS_TOOLS, JARVIS_MODEL, readRunbook, checkReadOnly } from "../jarvis.js";

export const chatRouter = Router();
const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MCP_URL = process.env.MCP_SERVER_URL || "http://hpe-mcp:8000/mcp";
const MAX_TURNS = 25;

// ── MCP session management ────────────────────────────────────────────────────
// Exported so jarvisAgent.js (the autopilot poller's investigation runner) can
// reuse the exact same session/call plumbing instead of a second implementation.
export async function initSession() {
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

export async function mcpCall(sessionId, method, params = {}) {
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

const ASSISTANT_SYSTEM = `You are a network operations assistant with FULL ACCESS to all six HPE networking platforms:
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

Always format responses as markdown tables. Be concise and direct.`;

// ── POST /api/chat ─────────────────────────────────────────────────────────────
chatRouter.post("/", async (req, res) => {
  const messages = req.body && req.body.messages;
  if (!messages || !Array.isArray(messages))
    return res.status(400).json({ error: "messages array required" });

  const jarvis = req.body.mode === "jarvis" || req.remote === true;
  const model = jarvis ? JARVIS_MODEL : "claude-sonnet-4-5";
  const system = jarvis ? JARVIS_SYSTEM : ASSISTANT_SYSTEM;
  const tools = jarvis ? JARVIS_TOOLS : TOOLS;
  const maxTokens = jarvis ? 8192 : 4096;

  res.setHeader("X-Netops-Mode", jarvis ? "jarvis" : "assistant");
  res.setHeader("Content-Type", "text/event-stream");
  res.setHeader("Cache-Control", "no-cache");
  res.setHeader("Connection", "keep-alive");
  res.flushHeaders();

  const send = (event, data) =>
    res.write("event: " + event + "\ndata: " + JSON.stringify(data) + "\n\n");

  try {
    const sessionId = await initSession();

    let currentMessages = [...messages];

    for (let turn = 0; turn < MAX_TURNS; turn++) {
      const response = await client.messages.create({
        model,
        max_tokens: maxTokens,
        system,
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
        const label = toolUse.input.description || (toolUse.name === "read_runbook" ? "runbook: " + (toolUse.input.name || "list") : toolUse.name);
        send("tool_start", { name: label });
        console.log("Executing:", label);

        try {
          let resultText;
          if (jarvis && toolUse.name === "read_runbook") {
            resultText = readRunbook(toolUse.input.name);
          } else {
            const blocked = jarvis ? checkReadOnly(toolUse.input.code || "") : null;
            if (blocked) {
              toolResults.push({
                type: "tool_result",
                tool_use_id: toolUse.id,
                content: [{ type: "text", text: blocked }],
                is_error: true,
              });
              send("tool_end", { name: label });
              continue;
            }
            const result = await mcpCall(sessionId, "tools/call", {
              name: "execute",
              arguments: { code: toolUse.input.code }
            });
            resultText = result?.content?.[0]?.text || JSON.stringify(result);
          }
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
        send("tool_end", { name: label });
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
