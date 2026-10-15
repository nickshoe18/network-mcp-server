import fs from "node:fs";
import path from "node:path";
import { getActiveMarvisActions, getSleBreaches, marvisConfigured } from "./marvisClient.js";
import { getSiteAlerts, severityScore } from "./centralClient.js";
import { runJarvisInvestigation, proposeRemediation, verifyRemediation } from "./jarvisAgent.js";
import { executeRemediation, remediationEnabled } from "./remediation.js";
import { evaluateRemediation } from "./remediationPolicy.js";
import { executeAndVerify, hasPreviousActionAttempt, preserveLatestActionState } from "./remediationLifecycle.js";
import { notify } from "./notifier.js";

const DATA_DIR = process.env.JARVIS_DATA_DIR || "/app/data";
const SEEN_FILE = path.join(DATA_DIR, "jarvis_seen_actions.json");
const SEEN_SLE_FILE = path.join(DATA_DIR, "jarvis_seen_sle.json");
const ACTIVE_SNAPSHOT_FILE = path.join(DATA_DIR, "jarvis_active_snapshot.json");
const PENDING_RESOLUTION_FILE = path.join(DATA_DIR, "jarvis_pending_resolution.json");
const ENTITY_ALERT_FILE = path.join(DATA_DIR, "jarvis_entity_last_alert.json");
const CENTRAL_SEEN_FILE = path.join(DATA_DIR, "jarvis_seen_central_alerts.json");
const CENTRAL_ACTIVE_SNAPSHOT_FILE = path.join(DATA_DIR, "jarvis_central_active_snapshot.json");
const CENTRAL_PENDING_RESOLUTION_FILE = path.join(DATA_DIR, "jarvis_central_pending_resolution.json");
const FINDINGS_FILE = path.join(DATA_DIR, "jarvis_findings.json");
const MAX_FINDINGS = 50;

const POLL_INTERVAL_MS = Number(process.env.JARVIS_POLL_INTERVAL_MS || 120000);
// SLE breach episodes: Mist's "hourly" bucket boundary doesn't actually stay fixed
// between polls (it was observed shifting every ~2 minutes), so deduping by bucket id
// re-alerted on every single poll cycle for one ongoing condition. Instead we track
// one open episode per metric: alert once when it starts, stay quiet while it's
// still the same episode, send at most one reminder per cooldown window if it drags
// on, and send one resolution alert when it clears — same shape as Marvis actions.
const SLE_EPISODE_GAP_MS = Number(process.env.JARVIS_SLE_EPISODE_GAP_MS || 90 * 60 * 1000); // gap bigger than this = new episode, not a continuation
const SLE_RENOTIFY_COOLDOWN_MS = Number(process.env.JARVIS_SLE_RENOTIFY_COOLDOWN_MS || 4 * 60 * 60 * 1000); // reminder cadence for a still-ongoing episode
// Marvis's "active actions" list has been observed to drop an action for a single poll
// and then list it again right after — treating one missed poll as "resolved" fired a
// fresh investigation + email every time that happened, repeatedly, for the same still-
// open issue. Require the action to be absent for this many consecutive polls before
// treating it as genuinely resolved.
const RESOLUTION_CONFIRM_POLLS = Number(process.env.JARVIS_RESOLUTION_CONFIRM_POLLS || 2);
// If the same entity (device) throws another new Marvis action within this window of its
// last alert, it's flapping, not a new independent problem — skip the costly investigation
// and email, and just leave a cheap pointer back at the earlier ticket.
const ENTITY_ALERT_COOLDOWN_MS = Number(process.env.JARVIS_ENTITY_ALERT_COOLDOWN_MS || 30 * 60 * 1000);
const ENABLED = (process.env.JARVIS_AUTOPILOT_ENABLED ?? "true") !== "false";
const MIST_ORG_ID = process.env.MIST_ORG_ID || "5f24e447-1145-4efa-94e0-ccec1a2a00a7"; // Stark Industries (lab)
const MIST_SITE_ID = process.env.MIST_SITE_ID || "59f74351-5c94-49bf-adea-dc96f4b132bf"; // Stark Tower (lab)
// Lab Central sites to poll for alerts — Hall of Justice + Bat Cave. Sandbox Testing is
// excluded on purpose: it's an empty validation sandbox with 0 devices, nothing will ever
// alert there.
const CENTRAL_SITE_IDS = (process.env.CENTRAL_SITE_IDS || "44056656981,791595406")
  .split(",").map(s => s.trim()).filter(Boolean);

function ensureDataDir() {
  try { fs.mkdirSync(DATA_DIR, { recursive: true }); } catch {}
}

function loadJson(file, fallback) {
  try { return JSON.parse(fs.readFileSync(file, "utf8")); } catch { return fallback; }
}

function saveJson(file, value) {
  try {
    fs.writeFileSync(file, JSON.stringify(value));
    return true;
  } catch (e) {
    console.error(`[poller] failed to write ${file}:`, e.message);
    return false;
  }
}

function describeAction(action) {
  const category = action.category || "unknown";
  const symptom = action.symptom || action.details?.reason || action.details?.failure_reason || "unspecified issue";
  const entityType = action.entity_type || action.display_entity_type || "network";
  const entityId = action.display_entity_id || action.entity_id || "";
  return { category, symptom, entityType, entityId, severity: action.severity ?? null, uuid: action.uuid };
}

// Runs one investigation, records its evidence, then either executes one eligible
// action or leaves a narrowly-scoped proposal for human review.
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
    actionDecision: { status: "not_evaluated" },
  };

  if (offerAction) {
    try {
      const observedEvidence = Array.isArray(result.observedEvidence) ? result.observedEvidence.join("\n\n") : "";
      const investigationIncomplete = result.text.includes("investigation did not conclude within the turn limit");
      if (!observedEvidence || !result.evidenceCapturedAt || investigationIncomplete) {
        record.actionDecision = {
          status: "blocked",
          reason: investigationIncomplete
            ? "Investigation did not conclude; no action was considered."
            : "No timestamped direct read-only evidence was available; no action was considered.",
        };
      } else {
        const proposal = await proposeRemediation(
          result.text,
          `[${trigger.source}] ${trigger.category}: ${trigger.symptom} (${trigger.entity})`,
          Array.isArray(result.observedEvidence) ? result.observedEvidence : [],
          result.evidenceCapturedAt,
        );
        if (proposal.proposal !== "no_action") {
          const eligibility = evaluateRemediation(proposal, observedEvidence, trigger.source, remediationEnabled());
          const previousAttempt = hasPreviousActionAttempt(findings, trigger.id);
          record.proposedAction = {
            name: proposal.proposal,
            params: proposal.params,
            reason: proposal.reason,
            confidence: eligibility.confidence,
            evidenceFor: proposal.evidenceFor,
            evidenceAgainst: proposal.evidenceAgainst,
            evidenceCapturedAt: proposal.evidenceCapturedAt,
            eligibility,
            status: !eligibility.approvalEligible ? "blocked"
              : !remediationEnabled() ? "disabled"
                : eligibility.autonomousEligible && previousAttempt ? "not_run"
                  : eligibility.autonomousEligible ? "executing" : "pending",
            executionMode: eligibility.autonomousEligible && !previousAttempt ? "autonomous"
              : eligibility.approvalEligible && remediationEnabled() && !eligibility.autonomousEligible ? "human_approval"
                : "none",
            createdAt: new Date().toISOString(),
          };
          record.actionDecision = {
            status: record.proposedAction.status,
            reason: previousAttempt && eligibility.autonomousEligible
              ? "An action was already attempted for this alert; Jarvis will not retry it."
              : eligibility.reason,
            checks: eligibility.checks,
          };

          if (record.proposedAction.status === "executing") {
            record.proposedAction.executionStartedAt = new Date().toISOString();
            findings.unshift(record);
            persistFindings(findings);
            const outcome = await executeAndVerify(
              { name: proposal.proposal, params: proposal.params, reason: proposal.reason },
              executeRemediation,
              verifyRemediation,
            );
            record.proposedAction.status = outcome.status;
            record.proposedAction.result = outcome.result;
            record.proposedAction.executedAt = new Date().toISOString();
            record.proposedAction.verification = outcome.verification;
            record.actionDecision.status = record.proposedAction.status;
            persistFindings(findings);
          } else if (!eligibility.approvalEligible) {
            record.actionDecision.status = "blocked";
            record.actionDecision.reason = eligibility.reason;
          }
        } else {
          record.actionDecision = {
            status: "no_action",
            reason: proposal.reason,
            confidence: proposal.confidence,
          };
        }
      }
    } catch (e) {
      console.error("[poller] proposeRemediation failed:", e.message);
      record.actionDecision = { status: "decision_failed", reason: e.message };
    }
  }

  if (!findings.includes(record)) {
    findings.unshift(record);
    persistFindings(findings);
  }
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

function entityKey(entityType, entityId) {
  return `${entityType}:${entityId}`.toLowerCase();
}

async function pollMarvisActions(findings) {
  const actions = await getActiveMarvisActions(MIST_ORG_ID); // may be [] — still need to run below for resolution detection
  const list = Array.isArray(actions) ? actions : [];
  const currentActiveIds = new Set(list.filter(a => a.uuid).map(a => a.uuid));
  const trackedIds = new Set(loadJson(ACTIVE_SNAPSHOT_FILE, []));
  const pendingResolution = loadJson(PENDING_RESOLUTION_FILE, {});
  const entityAlerts = loadJson(ENTITY_ALERT_FILE, {});
  const now = Date.now();

  const seen = new Set(loadJson(SEEN_FILE, []));
  const newActions = list.filter(a => a.uuid && !seen.has(a.uuid));

  if (newActions.length > 0) {
    console.log(`[poller] ${newActions.length} new active Marvis action(s)`);
    for (const action of newActions) {
      const d = describeAction(action);
      seen.add(d.uuid);
      delete pendingResolution[d.uuid]; // it's active again — cancel any resolution confirmation in progress

      const key = entityKey(d.entityType, d.entityId);
      const lastAlert = entityAlerts[key];
      if (lastAlert && (now - lastAlert) < ENTITY_ALERT_COOLDOWN_MS) {
        console.log(`[poller] suppressing repeat alert for ${key} — within flap cooldown`);
        findings.unshift({
          id: d.uuid,
          timestamp: new Date().toISOString(),
          trigger: {
            id: d.uuid, source: "marvis_actions", category: d.category, symptom: d.symptom,
            entity: `${d.entityType} ${d.entityId}`.trim(), severity: d.severity,
          },
          finding: `Suppressed — another alert for this entity fired within the last ${Math.round(ENTITY_ALERT_COOLDOWN_MS / 60000)} minutes ` +
            `(flap cooldown). No new investigation was run and no notification was sent; see the earlier ticket for this entity.`,
          toolLog: [],
          suppressed: true,
        });
        continue;
      }
      entityAlerts[key] = now;

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

  // Resolution detection, debounced: only confirm once an id has been missing from the
  // active list for RESOLUTION_CONFIRM_POLLS consecutive polls in a row.
  const resolvedNow = [];
  for (const id of trackedIds) {
    if (currentActiveIds.has(id)) {
      delete pendingResolution[id];
      continue;
    }
    pendingResolution[id] = (pendingResolution[id] || 0) + 1;
    if (pendingResolution[id] >= RESOLUTION_CONFIRM_POLLS) {
      resolvedNow.push(id);
      delete pendingResolution[id];
    }
  }

  if (resolvedNow.length > 0) {
    console.log(`[poller] ${resolvedNow.length} Marvis action(s) confirmed cleared — confirming resolution`);
    for (const id of resolvedNow) {
      await investigateResolution(id, findings);
      seen.delete(id); // let a genuine recurrence be treated as new again instead of going silent
    }
    saveJson(SEEN_FILE, [...seen].slice(-500));
  }

  const newTracked = new Set([...trackedIds].filter(id => !resolvedNow.includes(id)));
  for (const id of currentActiveIds) newTracked.add(id);

  saveJson(ACTIVE_SNAPSHOT_FILE, [...newTracked]);
  saveJson(PENDING_RESOLUTION_FILE, pendingResolution);
  saveJson(ENTITY_ALERT_FILE, entityAlerts);
}

async function pollSleBreaches(findings) {
  const breaches = await getSleBreaches(MIST_SITE_ID);

  const raw = loadJson(SEEN_SLE_FILE, {});
  const episodes = Array.isArray(raw) ? {} : raw; // migrate old array-of-ids format by discarding it
  const now = Date.now();
  const currentMetrics = new Set(breaches.map(b => b.metric));

  for (const b of breaches) {
    const prior = episodes[b.metric];
    const bucketMs = b.bucketStart * 1000;
    const gapMs = prior ? bucketMs - prior.lastBucketMs : Infinity;
    const isNewEpisode = !prior || gapMs > SLE_EPISODE_GAP_MS;
    const dueForReminder = prior && !isNewEpisode && (now - prior.lastNotifiedAt) >= SLE_RENOTIFY_COOLDOWN_MS;

    if (isNewEpisode || dueForReminder) {
      console.log(`[poller] SLE breach — ${b.metric} (${isNewEpisode ? "new episode" : "still ongoing, reminder"})`);

      const prompt = isNewEpisode
        ? `Mist's SLE (Service Level Experience) tracking just logged degraded minutes on the "${b.metric}" ` +
          `metric at Stark Tower — ${b.degradedMinutes.toFixed(1)} minutes in the last hour, driven by: ${b.classifiers.join(", ")}. ` +
          `Investigate what's causing it and report findings using your normal ticket format.`
        : `Mist's SLE tracking for the "${b.metric}" metric at Stark Tower is still showing degraded minutes ` +
          `(${b.degradedMinutes.toFixed(1)} in the last hour, driven by: ${b.classifiers.join(", ")}) — this has been ongoing. ` +
          `Re-check current state and report using your normal ticket format, noting whether it's gotten better or worse.`;

      await investigateAndRecord(prompt, {
        id: `${b.id}:${now}`, source: "sle", category: "sle", symptom: `${b.metric} degraded (${b.classifiers.join(", ")})`,
        entity: "Stark Tower", severity: null,
      }, findings);

      episodes[b.metric] = { lastBucketMs: bucketMs, lastNotifiedAt: now };
    } else {
      episodes[b.metric] = { ...prior, lastBucketMs: bucketMs };
    }
  }

  // Resolution: a metric with an open episode that's no longer breaching.
  for (const metric of Object.keys(episodes)) {
    if (currentMetrics.has(metric)) continue;
    console.log(`[poller] SLE breach cleared — ${metric}`);

    await investigateAndRecord(
      `Mist's SLE tracking for the "${metric}" metric at Stark Tower is no longer showing degraded minutes in the ` +
      `latest hourly bucket. Don't just trust that — independently re-check current state and confirm whether it's ` +
      `actually healthy now, using your normal ticket format.`,
      { id: `sle:${metric}:resolved:${now}`, source: "sle", category: "sle", symptom: `resolved: ${metric} degraded`, entity: "Stark Tower", severity: null },
      findings
    );
    delete episodes[metric];
  }

  saveJson(SEEN_SLE_FILE, episodes);
}

function describeCentralAlert(alert) {
  return {
    key: alert.key,
    category: alert.category || "unknown",
    name: alert.name || "alert",
    summary: alert.summary || "unspecified issue",
    deviceType: alert.device_type || "device",
    severity: severityScore(alert.severity),
  };
}

// Central alert cleared off the active list is the trigger, not the confirmation — same
// independent-reverify shape as investigateResolution above, for Central-sourced findings.
async function investigateCentralResolution(id, findings) {
  const original = findings.find(f => f.id === id && f.trigger?.source === "central_alerts");
  const category = original?.trigger?.category || "unknown";
  const symptom = original?.trigger?.symptom || "a previously flagged issue";
  const entity = original?.trigger?.entity || "";

  const prompt = `Aruba Central previously flagged this as an active alert and it's no longer listed as active. ` +
    `Don't just trust that — independently re-check the current state of the affected entity and confirm ` +
    `whether it's actually healthy now, using your normal ticket format. Note anything still worth watching.\n\n` +
    `Original issue — Category: ${category}\nSymptom: ${symptom}\nAffected: ${entity}` +
    (original ? `\n\nOriginal finding for context:\n\n${original.finding}` : "");

  await investigateAndRecord(prompt, {
    id: `${id}:resolved:${Date.now()}`, source: "central_alerts", category,
    symptom: `resolved: ${symptom}`, entity, severity: original?.trigger?.severity ?? null,
  }, findings);
}

// Mirrors pollMarvisActions' new/resolved/debounce/cooldown shape exactly, against Central's
// own alert feed instead. Central has no org-wide equivalent of Marvis Actions — alerts are
// per-site, so this loops CENTRAL_SITE_IDS. The flap-cooldown store (ENTITY_ALERT_FILE) is
// shared with Marvis's; the key namespaces don't collide (central:... vs type:id), and "don't
// re-investigate the same device too often" is the same rule regardless of which platform
// raised it.
async function pollCentralAlerts(findings) {
  const now = Date.now();
  const allAlerts = [];
  for (const siteId of CENTRAL_SITE_IDS) {
    const alerts = await getSiteAlerts(siteId);
    allAlerts.push(...alerts);
  }
  const activeAlerts = allAlerts.filter(a => a.status === "Active" && a.key);
  const currentActiveIds = new Set(activeAlerts.map(a => a.key));
  const trackedIds = new Set(loadJson(CENTRAL_ACTIVE_SNAPSHOT_FILE, []));
  const pendingResolution = loadJson(CENTRAL_PENDING_RESOLUTION_FILE, {});
  const entityAlerts = loadJson(ENTITY_ALERT_FILE, {});

  const seen = new Set(loadJson(CENTRAL_SEEN_FILE, []));
  const newAlerts = activeAlerts.filter(a => !seen.has(a.key));

  if (newAlerts.length > 0) {
    console.log(`[poller] ${newAlerts.length} new active Central alert(s)`);
    for (const alert of newAlerts) {
      const d = describeCentralAlert(alert);
      seen.add(d.key);
      delete pendingResolution[d.key];

      // No structured device id on the alert itself (confirmed against the real API) — the
      // alert's own summary text is the best available flap-identity proxy; it names the
      // specific device in practice ("...stopped receiving data from switch 6300").
      const key = `central:${d.deviceType}:${d.summary}`.toLowerCase();
      const lastAlert = entityAlerts[key];
      if (lastAlert && (now - lastAlert) < ENTITY_ALERT_COOLDOWN_MS) {
        console.log(`[poller] suppressing repeat Central alert for ${key} — within flap cooldown`);
        findings.unshift({
          id: d.key,
          timestamp: new Date().toISOString(),
          trigger: { id: d.key, source: "central_alerts", category: d.category, symptom: d.summary, entity: d.deviceType, severity: d.severity },
          finding: `Suppressed — another alert for this entity fired within the last ${Math.round(ENTITY_ALERT_COOLDOWN_MS / 60000)} minutes ` +
            `(flap cooldown). No new investigation was run and no notification was sent; see the earlier ticket for this entity.`,
          toolLog: [],
          suppressed: true,
        });
        continue;
      }
      entityAlerts[key] = now;

      const prompt = `Aruba Central just flagged a new active alert. Investigate it and report findings using your normal ticket format.\n\n` +
        `Category: ${d.category}\nAlert type: ${d.name}\nDevice type: ${d.deviceType}\nSummary: ${d.summary}\nSeverity: ${alert.severity ?? "n/a"}`;

      await investigateAndRecord(prompt, {
        id: d.key, source: "central_alerts", category: d.category, symptom: d.summary, entity: d.deviceType, severity: d.severity,
      }, findings, true);
    }
    saveJson(CENTRAL_SEEN_FILE, [...seen].slice(-500));
  }

  const resolvedNow = [];
  for (const id of trackedIds) {
    if (currentActiveIds.has(id)) { delete pendingResolution[id]; continue; }
    pendingResolution[id] = (pendingResolution[id] || 0) + 1;
    if (pendingResolution[id] >= RESOLUTION_CONFIRM_POLLS) { resolvedNow.push(id); delete pendingResolution[id]; }
  }

  if (resolvedNow.length > 0) {
    console.log(`[poller] ${resolvedNow.length} Central alert(s) confirmed cleared — confirming resolution`);
    for (const id of resolvedNow) {
      await investigateCentralResolution(id, findings);
      seen.delete(id);
    }
    saveJson(CENTRAL_SEEN_FILE, [...seen].slice(-500));
  }

  const newTracked = new Set([...trackedIds].filter(id => !resolvedNow.includes(id)));
  for (const id of currentActiveIds) newTracked.add(id);

  saveJson(CENTRAL_ACTIVE_SNAPSHOT_FILE, [...newTracked]);
  saveJson(CENTRAL_PENDING_RESOLUTION_FILE, pendingResolution);
  saveJson(ENTITY_ALERT_FILE, entityAlerts);
}

async function pollOnce() {
  const findings = loadJson(FINDINGS_FILE, []);
  const before = findings.length;

  if (marvisConfigured()) {
    await pollMarvisActions(findings);
    await pollSleBreaches(findings);
  }
  await pollCentralAlerts(findings);

  if (findings.length !== before) {
    persistFindings(findings);
  }
}

export function getFindings() {
  return loadJson(FINDINGS_FILE, []);
}

export function persistFindings(findings) {
  ensureDataDir();
  const temporaryFile = `${FINDINGS_FILE}.tmp`;
  // Poller snapshots can outlive an approval request; merge forward-only action
  // states before writing so an older snapshot cannot make an action retryable.
  const current = new Map(loadJson(FINDINGS_FILE, []).map(finding => [
    `${finding.id}:${finding.timestamp}`,
    finding,
  ]));
  const merged = findings.map(finding => preserveLatestActionState(
    finding,
    current.get(`${finding.id}:${finding.timestamp}`),
  ));
  try {
    fs.writeFileSync(temporaryFile, JSON.stringify(merged.slice(0, MAX_FINDINGS)));
    fs.renameSync(temporaryFile, FINDINGS_FILE);
  } catch (error) {
    try { fs.unlinkSync(temporaryFile); } catch (cleanupError) {
      if (cleanupError.code !== "ENOENT") console.error(`[poller] failed to remove ${temporaryFile}:`, cleanupError.message);
    }
    console.error(`[poller] failed to persist ${FINDINGS_FILE}:`, error.message);
    throw new Error("Failed to persist Jarvis findings; refusing to run or approve remediation.");
  }
}

// Read-modify-write one finding for the human approval route. persistFindings()
// keeps lifecycle transitions monotonic if a poller snapshot races this update.
export function updateFinding(id, updater) {
  const findings = loadJson(FINDINGS_FILE, []);
  const idx = findings.findIndex(f => f.id === id);
  if (idx === -1) return null;
  updater(findings[idx]);
  persistFindings(findings);
  return findings[idx];
}

// A full investigation (up to 15 agentic turns) can easily run past POLL_INTERVAL_MS, and
// `seen`/snapshot files are only persisted once a whole pollOnce() cycle finishes — so without
// this guard, setInterval fires a second overlapping cycle that re-reads the stale, not-yet-
// updated seen set and re-investigates the exact same new issue a second time concurrently.
let pollInFlight = false;

async function pollOnceGuarded() {
  if (pollInFlight) {
    console.log("[poller] previous poll cycle still running — skipping this tick");
    return;
  }
  pollInFlight = true;
  try {
    await pollOnce();
  } finally {
    pollInFlight = false;
  }
}

export function start() {
  if (!ENABLED) {
    console.log("[poller] JARVIS_AUTOPILOT_ENABLED=false — autopilot disabled");
    return;
  }
  ensureDataDir();
  if (!marvisConfigured()) {
    console.log("[poller] Marvis header file not found — marvis_actions/sle will stay idle until it's mounted (central_alerts is unaffected)");
  }
  console.log(`[poller] autopilot started — polling every ${POLL_INTERVAL_MS / 1000}s (marvis_actions + sle + central_alerts)`);
  pollOnceGuarded().catch(e => console.error("[poller] initial poll failed:", e.message));
  setInterval(() => {
    pollOnceGuarded().catch(e => console.error("[poller] poll cycle failed:", e.message));
  }, POLL_INTERVAL_MS);
}
