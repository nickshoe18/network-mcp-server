import fs from "node:fs";
import path from "node:path";
import { getActiveMarvisActions, getSleBreaches, marvisConfigured } from "./marvisClient.js";
import { runJarvisInvestigation, proposeRemediation } from "./jarvisAgent.js";
import { notify } from "./notifier.js";

const DATA_DIR = process.env.JARVIS_DATA_DIR || "/app/data";
const SEEN_FILE = path.join(DATA_DIR, "jarvis_seen_actions.json");
const SEEN_SLE_FILE = path.join(DATA_DIR, "jarvis_seen_sle.json");
const ACTIVE_SNAPSHOT_FILE = path.join(DATA_DIR, "jarvis_active_snapshot.json");
const FINDINGS_FILE = path.join(DATA_DIR, "jarvis_findings.json");
const MAX_FINDINGS = 50;

const POLL_INTERVAL_MS = Number(process.env.JARVIS_POLL_INTERVAL_MS || 120000);
const ENABLED = (process.env.JARVIS_AUTOPILOT_ENABLED ?? "true") !== "false";
const MIST_ORG_ID = process.env.MIST_ORG_ID || "5f24e447-1145-4efa-94e0-ccec1a2a00a7"; // Stark Industries (lab)
const MIST_SITE_ID = process.env.MIST_SITE_ID || "59f74351-5c94-49bf-adea-dc96f4b132bf"; // Stark Tower (lab)

function ensureDataDir() {
  try { fs.mkdirSync(DATA_DIR, { recursive: true }); } catch {}
}

function loadJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; }
}

function saveJson(file, value) {
  try { fs.writeFileSync(file, JSON.stringify(value)); } catch (e) { console.error(`[poller] failed to write ${file}:`, e.message); }
}

function describeAction(action) {
  const category = action.category || "unknown";
  const symptom = action.symptom || action.details?.reason || action.details?.failure_reason || "unspecified issue";
  const entityType = action.entity_type || action.display_entity_type || "network";
  const entityId = action.display_entity_id || action.entity_id || "";
  return { category, symptom, entityType, entityId, severity: action.severity ?? null, uuid: action.uuid };
}

// Runs one investigation and appends its result to the shared findings store.
// `trigger` is the compact summary shown in the UI list before expanding. When
// `offerAction` is set, also asks Jarvis to PROPOSE (never execute) one of the 3
// approved remediation actions — stored on the record for a human to approve via
// POST /api/findings/:id/approve. Only used for genuinely new issues, never for
// resolution confirmations (nothing to remediate once it's already clearing).
async function investigateAndRecord(prompt, trigger, findings, offerAction = false) {
  console.log(`[poller] investigating: ${trigger.symptom}`);
  let result;
  try {
    result = await runJarvisInvestigation(prompt);
  } catch (e) {
    console.error("[poller] investigation failed:", e.message);
    result = { text: `Investigation failed to run: ${e.message}`, toolLog: [] };
  }
  const record = {
    id: trigger.id,
    timestamp: new Date().toISOString(),
    trigger,
    finding: result.text,
    toolLog: result.toolLog,
  };

  if (offerAction) {
    try {
      const proposal = await proposeRemediation(result.text, `${trigger.category}: ${trigger.symptom} (${trigger.entity})`);
      if (proposal.proposal !== "no_action") {
        record.proposedAction = { name: proposal.proposal, params: proposal.params, reason: proposal.reason, status: "pending" };
        console.log(`[poller] proposed action: ${proposal.proposal} — ${proposal.reason}`);
      }
    } catch (e) {
      console.error("[poller] proposeRemediation failed:", e.message);
    }
  }

  findings.unshift(record);
  notify(record).catch(e => console.error("[poller] notify failed:", e.message));
}

// Marvis dropping an action off its active list is the trigger, not the confirmation —
// this runs a real Jarvis investigation to independently verify the entity is actually
// healthy now (not just that Marvis stopped complaining), same ticket format as the
// original alert, explicitly referencing it for continuity.
async function investigateResolution(id, findings) {
  const original = findings.find(f => f.id === id && f.trigger?.source === "marvis_actions");
  const category = original?.trigger?.category || "unknown";
  const symptom = original?.trigger?.symptom || "a previously flagged issue";
  const entity = original?.trigger?.entity || "";

  const prompt = `Marvis previously flagged this as an active issue and has now stopped listing it as active. ` +
    `Don't just trust that flag — independently re-check the current state of the affected entity and confirm ` +
    `whether it's actually healthy now, using your normal ticket format. Note anything still worth watching.\n\n` +
    `Original issue — Category: ${category}\nSymptom: ${symptom}\nAffected: ${entity}` +
    (original ? `\n\nOriginal finding for context:\n\n${original.finding}` : "");

  await investigateAndRecord(prompt, {
    id: `${id}:resolved:${Date.now()}`, source: "marvis_actions", category,
    symptom: `resolved: ${symptom}`, entity, severity: original?.trigger?.severity ?? null,
  }, findings);
}

async function pollMarvisActions(findings) {
  const actions = await getActiveMarvisActions(MIST_ORG_ID); // may be [] — still need to run below for resolution detection
  const list = Array.isArray(actions) ? actions : [];
  const currentActiveIds = new Set(list.filter(a => a.uuid).map(a => a.uuid));
  const previousActiveIds = new Set(loadJson(ACTIVE_SNAPSHOT_FILE, []));

  const seen = new Set(loadJson(SEEN_FILE, []));
  const newActions = list.filter(a => a.uuid && !seen.has(a.uuid));

  if (newActions.length > 0) {
    console.log(`[poller] ${newActions.length} new active Marvis action(s)`);
    for (const action of newActions) {
      const d = describeAction(action);
      seen.add(d.uuid);

      const prompt = `Marvis just flagged a new active issue. Investigate it and report findings using your normal ticket format.\n\n` +
        `Category: ${d.category}\nSymptom: ${d.symptom}\nAffected: ${d.entityType} ${d.entityId}\nSeverity: ${d.severity ?? "n/a"}\n` +
        `Raw Marvis suggestion: ${action.suggestion || "none"}`;

      await investigateAndRecord(prompt, {
        id: d.uuid, source: "marvis_actions", category: d.category, symptom: d.symptom,
        entity: `${d.entityType} ${d.entityId}`.trim(), severity: d.severity,
      }, findings, true);
    }
    saveJson(SEEN_FILE, [...seen].slice(-500));
  }

  // Resolution detection: anything active last poll that's dropped off the active list now.
  const resolvedIds = [...previousActiveIds].filter(id => !currentActiveIds.has(id));
  if (resolvedIds.length > 0) {
    console.log(`[poller] ${resolvedIds.length} Marvis action(s) cleared — confirming resolution`);
    for (const id of resolvedIds) await investigateResolution(id, findings);
  }

  saveJson(ACTIVE_SNAPSHOT_FILE, [...currentActiveIds]);
}

async function pollSleBreaches(findings) {
  const breaches = await getSleBreaches(MIST_SITE_ID);
  if (breaches.length === 0) return;

  const seen = new Set(loadJson(SEEN_SLE_FILE, []));
  const newBreaches = breaches.filter(b => !seen.has(b.id));
  if (newBreaches.length === 0) return;

  console.log(`[poller] ${newBreaches.length} new SLE breach(es)`);

  for (const b of newBreaches) {
    seen.add(b.id);

    const prompt = `Mist's SLE (Service Level Experience) tracking just logged degraded minutes on the "${b.metric}" ` +
      `metric at Stark Tower — ${b.degradedMinutes.toFixed(1)} minutes in the last hour, driven by: ${b.classifiers.join(", ")}. ` +
      `Investigate what's causing it and report findings using your normal ticket format.`;

    await investigateAndRecord(prompt, {
      id: b.id, source: "sle", category: "sle", symptom: `${b.metric} degraded (${b.classifiers.join(", ")})`,
      entity: "Stark Tower", severity: null,
    }, findings);
  }

  saveJson(SEEN_SLE_FILE, [...seen].slice(-500));
}

async function pollOnce() {
  if (!marvisConfigured()) return; // header file not mounted — silently a no-op

  const findings = loadJson(FINDINGS_FILE, []);
  const before = findings.length;

  await pollMarvisActions(findings);
  await pollSleBreaches(findings);

  if (findings.length !== before) {
    saveJson(FINDINGS_FILE, findings.slice(0, MAX_FINDINGS));
  }
}

export function getFindings() {
  return loadJson(FINDINGS_FILE, []);
}

// Read-modify-write a single finding by id. Used only by the human-approval route
// (routes/findings.js) to record an approval decision and its outcome — the poller's
// own writes to this same file are a full-array replace on a 2-minute cadence, and
// actual approvals are rare enough that a plain read-modify-write is fine here without
// adding file locking for a race window this narrow.
export function updateFinding(id, updater) {
  const findings = loadJson(FINDINGS_FILE, []);
  const idx = findings.findIndex(f => f.id === id);
  if (idx === -1) return null;
  updater(findings[idx]);
  saveJson(FINDINGS_FILE, findings);
  return findings[idx];
}

export function start() {
  if (!ENABLED) {
    console.log("[poller] JARVIS_AUTOPILOT_ENABLED=false — autopilot disabled");
    return;
  }
  ensureDataDir();
  if (!marvisConfigured()) {
    console.log("[poller] Marvis header file not found — autopilot will stay idle until it's mounted");
  }
  console.log(`[poller] autopilot started — polling every ${POLL_INTERVAL_MS / 1000}s (marvis_actions + sle)`);
  pollOnce().catch(e => console.error("[poller] initial poll failed:", e.message));
  setInterval(() => {
    pollOnce().catch(e => console.error("[poller] poll cycle failed:", e.message));
  }, POLL_INTERVAL_MS);
}
