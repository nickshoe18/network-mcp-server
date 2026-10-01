import fs from "node:fs";

// Dedicated, isolated MCP instance (hpe-mcp-autopilot in docker-compose.yml) — separate
// from MCP_SERVER_URL, which stays used for all read-only investigation. Only this client
// ever calls a write tool, and only for the 4 exact actions below.
const AUTOPILOT_MCP_URL = process.env.MCP_AUTOPILOT_SERVER_URL || "http://hpe-mcp-autopilot:8000/mcp";
const HDR = { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" };

// Master switch. Defaults OFF — building this does not make it live. Someone has to
// deliberately set JARVIS_REMEDIATION_ENABLED=true for the autopilot to ever execute
// anything; until then every action call below refuses before it would touch the network.
export function remediationEnabled() {
  return (process.env.JARVIS_REMEDIATION_ENABLED ?? "false") === "true";
}

let sessionId = null;

async function initSession() {
  const resp = await fetch(AUTOPILOT_MCP_URL, {
    method: "POST", headers: HDR,
    body: JSON.stringify({
      jsonrpc: "2.0", id: 0, method: "initialize",
      params: { protocolVersion: "2025-11-25", capabilities: {}, clientInfo: { name: "netops-backend-remediation", version: "1.0" } },
    }),
  });
  const sid = resp.headers.get("mcp-session-id") || resp.headers.get("x-mcp-session-id");
  await resp.text();
  return sid;
}

function parseResult(text) {
  for (const line of text.split("\n")) {
    if (!line.startsWith("data:")) continue;
    const parsed = JSON.parse(line.slice(5).trim());
    if (parsed.error) return { ok: false, error: JSON.stringify(parsed.error) };
    const content = parsed.result?.content?.[0];
    if (!content) return { ok: false, error: "empty response" };
    if (parsed.result?.isError) return { ok: false, error: content.text };
    try { return { ok: true, data: JSON.parse(content.text) }; } catch { return { ok: true, data: content.text }; }
  }
  return { ok: false, error: "no data in response" };
}

// The ONLY place `confirmed: true` is ever set — fixed infrastructure code, never
// LLM-generated text, and only reachable through the 4 narrow functions below, each of
// which accepts exactly the single-entity string params it names and nothing else.
async function callWriteTool(toolName, params) {
  if (!sessionId) sessionId = await initSession();
  const headers = { ...HDR, "mcp-session-id": sessionId };
  const resp = await fetch(AUTOPILOT_MCP_URL, {
    method: "POST", headers,
    body: JSON.stringify({
      jsonrpc: "2.0", id: Math.floor(Math.random() * 99999), method: "tools/call",
      params: { name: toolName, arguments: { ...params, confirmed: true } },
    }),
  });
  return parseResult(await resp.text());
}

function auditLog(action, params, result) {
  const line = `[remediation] ${action} ${JSON.stringify(params)} -> ${result.ok ? "ok" : "FAILED: " + result.error}`;
  console.log(line);
  return line;
}

// ── The 4 approved actions — each takes exactly the ids it names, nothing else ──

export async function rebootAp(site_id, device_id) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (JARVIS_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("mist_restart_site_device", { site_id, device_id });
  auditLog("reboot_ap", { site_id, device_id }, result);
  return result;
}

export async function disconnectClient(site_id, client_mac) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (JARVIS_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("mist_disconnect_site_wireless_client", { site_id, client_mac });
  auditLog("disconnect_client", { site_id, client_mac }, result);
  return result;
}

export async function setLocateLed(site_id, device_id, enabled) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (JARVIS_REMEDIATION_ENABLED != true)" };
  const tool = enabled ? "mist_start_site_locate_device" : "mist_stop_site_locate_device";
  const result = await callWriteTool(tool, { site_id, device_id });
  auditLog(enabled ? "locate_led_start" : "locate_led_stop", { site_id, device_id }, result);
  return result;
}

// release_dhcp_lease deliberately NOT implemented — the real request body shape for
// scoping the release to one client (vs. every lease on the device) couldn't be verified
// against authoritative docs. Add it only once that's confirmed against a real Mist
// dashboard API reference session, not guessed.
