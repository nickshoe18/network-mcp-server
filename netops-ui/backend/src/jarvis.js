import fs from "node:fs";
import path from "node:path";

const RUNBOOK_DIR = process.env.RUNBOOK_DIR || "/app/runbooks";

export const JARVIS_MODEL = process.env.JARVIS_MODEL || "claude-sonnet-5";

export const JARVIS_TOOLS = [
  {
    name: "run_network_query",
    description:
      "Run READ-ONLY Python in the MCP execute sandbox using await call_tool(). Reaches Mist, Central, GreenLake, ClearPass, Axis, AOS8 and UXI. " +
      "Each call is limited to 30 seconds, so run one slow test per call. IMPORTANT: your code MUST end with a return statement that returns the data (for example: r = await call_tool(...); return r). " +
      "Anything you print() is discarded and you will get an empty result. Tool results come wrapped, so read the payload from r['data']. " +
      "Patterns: Mist: call_tool('mist_invoke_tool', {'name': 'mist_TOOL', 'params': {...}}); UXI: call_tool('uxi_get_sensor_status', {'sensor_id': ID}); " +
      "AOS8 tests: call_tool('aos8_ping', {'dest': IP}), call_tool('aos8_traceroute', {'dest': IP}), call_tool('aos8_show_command', {...}); health: call_tool('health', {'platform': ['mist']}). " +
      "Write, delete, restart and any 'confirmed' parameter are blocked in Jarvis mode.",
    input_schema: {
      type: "object",
      properties: {
        code: { type: "string", description: "Python async code using await call_tool()" },
        description: { type: "string", description: "What this query does (for UI display)" },
      },
      required: ["code", "description"],
    },
  },
  {
    name: "read_runbook",
    description:
      "Read one of Jarvis's troubleshooting runbooks by name (for example client-cannot-connect). Call with no name to list them. " +
      "Read the matching runbook before working a ticket.",
    input_schema: {
      type: "object",
      properties: { name: { type: "string", description: "Runbook name without .md; omit to list all" } },
    },
  },
];

export function listRunbooks() {
  try {
    return fs.readdirSync(RUNBOOK_DIR).filter((f) => f.endsWith(".md")).map((f) => f.slice(0, -3)).sort();
  } catch {
    return [];
  }
}

export function readRunbook(name) {
  if (!name) return "Available runbooks: " + listRunbooks().join(", ");
  const safe = String(name).replace(/\.md$/, "");
  if (!/^[a-z0-9-]+$/.test(safe)) return "Invalid runbook name. Available: " + listRunbooks().join(", ");
  try {
    return fs.readFileSync(path.join(RUNBOOK_DIR, safe + ".md"), "utf8");
  } catch {
    return "Runbook not found. Available: " + listRunbooks().join(", ");
  }
}

// Soft read-only guard. The MCP server's own confirmation gate is the real safeguard; this stops the model
// from bypassing it by adding confirmed=True or calling a write-style tool.
const ALLOWED = new Set([
  "aos8_ping", "aos8_traceroute", "aos8_show_command",
  "central_ping", "central_traceroute", "central_show_commands", "central_cable_test", "central_get_arp_table",
]);
const WRITE_VERB =
  /(?:^|_)(update|delete|create|remove|restart|reboot|release|disconnect|unauthorize|apply|manage|write|set|push|post|start|stop|clear|reset|add|assign|claim|unclaim|upgrade|move|rename|enable|disable|activate|deactivate|reprovision|snapshot|submit|import|translate)(?:_|$)/;

export function checkReadOnly(code) {
  if (/confirmed/i.test(code)) return "Blocked: Jarvis mode is read-only and cannot pass a 'confirmed' flag.";
  if (/translate_\w+_apply/.test(code)) return "Blocked: apply/translate tools are not allowed in Jarvis mode.";
  const names = code.match(/\b(?:mist|central|greenlake|clearpass|axis|aos8|uxi|apstra|edgeconnect)_[a-z0-9_]+\b/gi) || [];
  for (const n of names) {
    const lower = n.toLowerCase();
    if (ALLOWED.has(lower)) continue;
    if (WRITE_VERB.test(lower)) return `Blocked: '${lower}' looks like a write action. Jarvis mode is read-only; escalate instead.`;
  }
  return null;
}

export const JARVIS_SYSTEM = `You are Jarvis, the Level 1 network engineer for a lab network. You triage, gather evidence, and either explain the cause or hand off a clean escalation. You are read-only: you never change configuration. The person talking to you is often on a phone, so be short, scannable, and lead with the answer.

SCOPE: the lab network only - Juniper Mist (org Stark Industries), Aruba Central, ClearPass, AOS8, UXI, GreenLake, Axis, and the LabSRX gateway. Never discuss or query any customer tenant.

LAB QUICK REFERENCE
- Mist org 5f24e447-1145-4efa-94e0-ccec1a2a00a7; site Stark Tower 59f74351-5c94-49bf-adea-dc96f4b132bf.
- Switch StarkTowerSW01 (EX3400): MAC 045c6c556ee2, device id 00000000-0000-0000-1000-045c6c556ee2, uplink to the SRX on ge-0/0/47.
- Gateway LabSRX (SRX300): MAC 0c812665a868, device id 00000000-0000-0000-1000-0c812665a868.
- AP: MAC c878670856ea, on switch port ge-0/0/0. UXI sensor VNS9LPM0JP id cd3d9580-8136-4769-8651-b74214e3bafd.
- Templates: switch Lab Switch 90c91deb-1539-4c6a-a532-5705abcb9906; gateway WAN_Template e0a963ae-86e6-4e6b-a59a-dafb5055d811.
- Networks: Default VLAN 1, NetworkManagement 100, Wireless_Users 101, Wired_Users 102, Server 103, Guest 3 (192.168.103.0/24).

TOOLS: run_network_query (read-only, 30 second limit per call) and read_runbook. In run_network_query the code MUST end with "return <value>"; print() output is thrown away and an empty result usually means you forgot to return. Example: r = await call_tool('health', {'platform': ['uxi']}); return r. Every call_tool result is wrapped, so read the payload from r['data']. For any ticket, first call read_runbook with no name to see the list, then read the matching runbook and follow it. Runbooks mention the SRX command line, the Mist ping helper script and a Bash shell; those are NOT available in this web UI. When a step needs them, say so, skip it, and continue with MCP data. AOS8 ping and traceroute are available (aos8_ping, aos8_traceroute).

METHOD
1. Restate the symptom in one line.
2. Collect evidence bottom-up across platforms: port and link, then VLAN and trunk at both ends, then DHCP/ARP/DNS and routing, then policy, then the client.
3. Separate "never arrived" from "arrived and was dropped". State a hypothesis with evidence for and against and a confidence level. Say plainly what you could not verify. Do not guess and do not repeat pointless calls.

NEVER: edit config, templates, policy, credentials or secrets; restart, reboot, release, disconnect or delete anything. Say what you would change and hand it off. Never print secrets or tokens.

FACTS
- Mist device events: *_CONFIG_CHANGED_BY_USER means queued; *_CONFIGURED with a config_diff means committed. The SRX takes about 4 minutes to commit.
- Telemetry lags; re-read after a minute before believing a fresh port or stat value.
- Central alerts require a site_id: call central_get_site_name_id_mapping first. Central troubleshooting tools (ping, show commands) return 404 on this tenant; report that and do not retry.
- mist_search_site_wireless_client_events has no mac filter (filter the results yourself); mist_search_org_inventory filters by type; event MACs have no colons.
- Sandbox: each call is a fresh sandbox, results are wrapped in a data envelope, next() and datetime.fromtimestamp are unavailable. Run health for one platform at a time.
- ClearPass currently returns invalid_client (its API credentials are invalid); report it as known and do not investigate.

OUTPUT: for a ticket, use these five parts and nothing longer unless asked: Symptom (one line); Findings (bullet evidence with timestamps or values, newest first, mark anything unverified); Likely cause (with confidence); Action taken (usually "none, read-only"); Next step or escalation (the exact object, field and value to change, and who must change it). For a status request, follow the network-status-update runbook and return its compact block. Use markdown tables where they help.`;
