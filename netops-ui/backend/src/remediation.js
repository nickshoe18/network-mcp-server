import fs from "node:fs";
import { fridaySetting } from "./fridayConfig.js";

// Dedicated, isolated MCP instance (hpe-mcp-autopilot in docker-compose.yml) — separate
// from MCP_SERVER_URL, which stays used for all read-only investigation. Only this client
// ever calls a write tool, and only for the 7 exact actions below.
const AUTOPILOT_MCP_URL = process.env.MCP_AUTOPILOT_SERVER_URL || "http://hpe-mcp-autopilot:8000/mcp";
const HDR = { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" };

// Master switch. Defaults OFF — building this does not make it live. Someone has to
// deliberately set FRIDAY_REMEDIATION_ENABLED=true for the autopilot to ever execute
// anything; until then every action call below refuses before it would touch the network.
export function remediationEnabled() {
  return fridaySetting("REMEDIATION_ENABLED", "false") === "true";
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
// LLM-generated text, and only reachable through the 7 narrow functions below, each of
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

// ── The 7 approved actions — each takes exactly the ids it names, nothing else ──

export async function rebootAp(site_id, device_id) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("mist_restart_site_device", { site_id, device_id });
  auditLog("reboot_ap", { site_id, device_id }, result);
  return result;
}

export async function disconnectClient(site_id, client_mac) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("mist_disconnect_site_wireless_client", { site_id, client_mac });
  auditLog("disconnect_client", { site_id, client_mac }, result);
  return result;
}

export async function setLocateLed(site_id, device_id, enabled) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  const tool = enabled ? "mist_start_site_locate_device" : "mist_stop_site_locate_device";
  const result = await callWriteTool(tool, { site_id, device_id });
  auditLog(enabled ? "locate_led_start" : "locate_led_stop", { site_id, device_id }, result);
  return result;
}

// Request shape confirmed against the real OpenAPI spec (schema utils_release_dhcp_leases,
// bundled spec_index.db) — `macs` + `network` releases exactly the named client leases on
// that network, scoped to one gateway device; `port_id` alone (not used here) would release
// every lease on a port instead, which is broader than FRIDAY should ever propose.
export async function releaseDhcpLease(site_id, device_id, macs, network) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("mist_release_site_device_dhcp_lease", { site_id, device_id, macs, network });
  auditLog("release_dhcp_lease", { site_id, device_id, macs, network }, result);
  return result;
}

// ── Aruba Central equivalents — same gate, same isolated instance, same audit log ──
// Central has no site_id/device_id pair like Mist; its device-level write tools address a
// device directly by device_family/serial_number (confirmed against the real tool schemas,
// central_get_tool_schema), so these take that shape instead.

export async function rebootCentralDevice(device_family, serial_number) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("central_reboot_device", { device_family, serial_number });
  auditLog("reboot_central_device", { device_family, serial_number }, result);
  return result;
}

// device_kind picks the right underlying Central tool — each targets a different device
// class with a different param name for the client MAC (confirmed per-tool via
// central_get_tool_schema: user_mac_address on an AP, mac_address + device_type on a
// switch, client_mac_address on a gateway).
export async function disconnectCentralClient(device_kind, serial_number, mac, switch_type) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  let tool, params;
  if (device_kind === "ap") { tool = "central_disconnect_user_by_mac_on_ap"; params = { serial_number, user_mac_address: mac }; }
  else if (device_kind === "switch") { tool = "central_disconnect_client_switch"; params = { serial_number, device_type: switch_type, mac_address: mac }; }
  else if (device_kind === "gateway") { tool = "central_disconnect_client_by_mac_on_gateway"; params = { serial_number, client_mac_address: mac }; }
  else return { ok: false, error: `unknown device_kind '${device_kind}'` };

  const result = await callWriteTool(tool, params);
  auditLog("disconnect_central_client", { device_kind, serial_number, mac }, result);
  return result;
}

export async function locateCentralDevice(device_family, serial_number) {
  if (!remediationEnabled()) return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  const result = await callWriteTool("central_locate_device", { device_family, serial_number });
  auditLog("locate_central_device", { device_family, serial_number }, result);
  return result;
}

export async function executeRemediation(name, params = {}) {
  if (!remediationEnabled()) {
    return { ok: false, error: "remediation disabled (FRIDAY_REMEDIATION_ENABLED != true)" };
  }
  if (name === "reboot_ap") return rebootAp(params.site_id, params.device_id);
  if (name === "disconnect_client") return disconnectClient(params.site_id, params.client_mac);
  if (name === "locate_led") return setLocateLed(params.site_id, params.device_id, params.enabled);
  if (name === "release_dhcp_lease") return releaseDhcpLease(params.site_id, params.device_id, params.macs, params.network);
  if (name === "reboot_central_device") return rebootCentralDevice(params.device_family, params.serial_number);
  if (name === "disconnect_central_client") {
    return disconnectCentralClient(params.device_kind, params.serial_number, params.mac, params.switch_type);
  }
  if (name === "locate_central_device") return locateCentralDevice(params.device_family, params.serial_number);
  return { ok: false, error: `unsupported remediation action '${name}'` };
}

// No Central equivalent of release_dhcp_lease was found — Central's DHCP tools
// (central_manage_dhcp_client, etc.) are config-object CRUD, not an operational
// "release this one client's lease now" action. Left out rather than guessed at.
