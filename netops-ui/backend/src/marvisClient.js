import fs from "node:fs";

const MARVIS_MCP_URL = process.env.MARVIS_MCP_URL || "https://mcp.ai.juniper.net/mcp/mist";
const HEADER_FILE = process.env.MARVIS_HEADER_FILE || "/run/secrets/juniper_mist_headers.txt";

// Parses mcp-remote's --header-file format: one "Name: value" per line, "#" starts a comment.
function readHeaders() {
  const headers = { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" };
  let raw;
  try {
    raw = fs.readFileSync(HEADER_FILE, "utf8");
  } catch {
    return null; // file missing — Marvis polling is disabled, not a fatal error for the rest of the backend
  }
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const idx = trimmed.indexOf(":");
    if (idx === -1) continue;
    const name = trimmed.slice(0, idx).trim();
    const value = trimmed.slice(idx + 1).trim();
    if (name) headers[name] = value;
  }
  return headers;
}

let sessionId = null;
let baseHeaders = null;

async function initSession() {
  baseHeaders = readHeaders();
  if (!baseHeaders) return null;
  const resp = await fetch(MARVIS_MCP_URL, {
    method: "POST",
    headers: baseHeaders,
    body: JSON.stringify({
      jsonrpc: "2.0", id: 0, method: "initialize",
      params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "netops-backend-marvis-poller", version: "1.0" } },
    }),
  });
  const sid = resp.headers.get("mcp-session-id") || resp.headers.get("x-mcp-session-id");
  await resp.text();
  return sid;
}

async function callTool(name, args) {
  if (!baseHeaders) baseHeaders = readHeaders();
  if (!baseHeaders) throw new Error("Marvis header file not found — autopilot polling disabled");
  if (!sessionId) sessionId = await initSession();

  const headers = { ...baseHeaders };
  if (sessionId) headers["mcp-session-id"] = sessionId;

  const resp = await fetch(MARVIS_MCP_URL, {
    method: "POST",
    headers,
    body: JSON.stringify({ jsonrpc: "2.0", id: Math.floor(Math.random() * 99999), method: "tools/call", params: { name, arguments: args } }),
  });

  if (resp.status === 401 || resp.status === 404) {
    // session likely expired server-side — reinit once and retry
    sessionId = await initSession();
    const retryHeaders = { ...baseHeaders };
    if (sessionId) retryHeaders["mcp-session-id"] = sessionId;
    const retry = await fetch(MARVIS_MCP_URL, {
      method: "POST", headers: retryHeaders,
      body: JSON.stringify({ jsonrpc: "2.0", id: Math.floor(Math.random() * 99999), method: "tools/call", params: { name, arguments: args } }),
    });
    return parseResult(await retry.text());
  }

  return parseResult(await resp.text());
}

function parseResult(text) {
  for (const line of text.split("\n")) {
    if (!line.startsWith("data:")) continue;
    const parsed = JSON.parse(line.slice(5).trim());
    if (parsed.error) throw new Error(`Marvis MCP error: ${JSON.stringify(parsed.error)}`);
    const content = parsed.result?.content?.[0];
    if (!content) return null;
    if (parsed.result?.isError) throw new Error(`Marvis tool error: ${content.text}`);
    try { return JSON.parse(content.text); } catch { return content.text; }
  }
  return null;
}

// Returns the array of currently-active Marvis Actions for one org, or [] if
// the header file is missing (feature simply stays off) or the call fails.
export async function getActiveMarvisActions(orgId) {
  try {
    const result = await callTool("get_mist_insights", {
      insight_type: "marvis_actions",
      org_id: orgId,
      params: { active: true },
    });
    return result?.data ?? [];
  } catch (err) {
    console.error("[marvisClient] getActiveMarvisActions failed:", err.message);
    return [];
  }
}

export function marvisConfigured() {
  return fs.existsSync(HEADER_FILE);
}

// The 7 site-level SLE metrics Mist tracks (per get_mist_constants('insight_metrics')).
const SLE_METRICS = ["coverage", "capacity", "roaming", "time-to-connect", "switch-health", "gateway-health", "wan-link-health"];

// Returns any SLE classifier that logged degraded minutes in the most recent
// hourly bucket, across all 7 metrics for one site. Each entry gets a stable
// id (metric + classifier + hour bucket) so the poller can dedup per-hour
// without re-alerting on every 2-minute poll within the same degraded hour.
export async function getSleBreaches(siteId) {
  const breaches = [];
  for (const metric of SLE_METRICS) {
    try {
      const result = await callTool("get_mist_insights", {
        insight_type: "sle",
        site_id: siteId,
        params: { query_type: "summary", scope: "site", scope_id: siteId, metric },
      });
      const sle = result?.data?.sle;
      const classifiers = result?.data?.classifiers || [];
      const bucketEnd = result?.data?.end; // epoch seconds, hour-aligned
      if (!sle?.samples?.degraded?.length || !bucketEnd) continue;

      const lastIdx = sle.samples.degraded.length - 1;
      const bucketStart = bucketEnd - sle.interval; // start of the most recent hourly bucket

      if (sle.samples.degraded[lastIdx] > 0) {
        // find which specific classifier(s) drove the degradation, for a richer trigger prompt
        const culprits = classifiers
          .filter(c => c.samples?.degraded?.[lastIdx] > 0)
          .map(c => c.name);
        breaches.push({
          id: `sle:${metric}:${bucketStart}`,
          metric,
          degradedMinutes: sle.samples.degraded[lastIdx],
          classifiers: culprits.length ? culprits : ["unspecified"],
          bucketStart,
        });
      }
    } catch (err) {
      console.error(`[marvisClient] getSleBreaches(${metric}) failed:`, err.message);
    }
  }
  return breaches;
}
