import { initSession, mcpCall } from "./routes/chat.js";

// Central alerts live inside the SAME hpe-mcp server Jarvis's own investigation already
// reaches (unlike Mist's Marvis Actions, which come from a separate external MCP server) —
// so this just runs a small `execute` sandbox call through the existing session/call
// plumbing chat.js already exports, no new MCP client or server needed.
let sessionId = null;

const SEVERITY_SCORE = { critical: 100, major: 80, warning: 50, minor: 40, info: 10 };

// Converts Central's categorical severity (Critical/Major/Warning/Minor/Info) to the same
// rough 0-100 scale Marvis severity already uses, so notifier.js's existing numeric
// NOTIFY_SEVERITY_FLOOR check works unchanged for Central-sourced findings too.
export function severityScore(severity) {
  return SEVERITY_SCORE[(severity || "").toLowerCase()] ?? null;
}

// Returns Central's alerts for one site, any status (the caller filters to Active). Central's
// own `data` is the literal string "No alerts found matching criteria" when empty, not an
// object — guarded below rather than assumed away.
export async function getSiteAlerts(siteId) {
  if (!sessionId) sessionId = await initSession();
  const code = `r = await call_tool('central_invoke_tool', {'name': 'central_get_alerts', 'params': {'site_id': '${siteId}'}})\nreturn r`;
  try {
    const result = await mcpCall(sessionId, "tools/call", { name: "execute", arguments: { code } });
    const text = result?.content?.[0]?.text;
    if (!text) return [];
    const parsed = JSON.parse(text);
    const items = parsed?.data?.items;
    return Array.isArray(items) ? items : [];
  } catch (e) {
    console.error(`[centralClient] getSiteAlerts(${siteId}) failed:`, e.message);
    return [];
  }
}
