import fs from "node:fs";

const TEAMS_WEBHOOK_FILE = process.env.TEAMS_WEBHOOK_FILE || "/run/secrets/teams_webhook_url.txt";
const RESEND_API_KEY_FILE = process.env.RESEND_API_KEY_FILE || "/run/secrets/resend_api_key.txt";
const EMAIL_FROM = process.env.NOTIFY_EMAIL_FROM || "";
const EMAIL_TO = (process.env.NOTIFY_EMAIL_TO || "").split(",").map(s => s.trim()).filter(Boolean);

// Only push external notifications for findings that clear this bar — everything
// still lands in the UI's Autonomous Findings panel regardless of severity.
// Marvis severity is roughly 0-100; SLE-sourced findings carry no severity field
// (null) and are treated as worth notifying on, since they're inherently rarer/real.
const SEVERITY_FLOOR = Number(process.env.NOTIFY_SEVERITY_FLOOR ?? 50);

function readSecretFile(path) {
  try { return fs.readFileSync(path, "utf8").trim(); } catch { return null; }
}

function shouldNotify(record) {
  const sev = record.trigger?.severity;
  return sev === null || sev === undefined || sev >= SEVERITY_FLOOR;
}

async function notifyTeams(record) {
  const webhookUrl = readSecretFile(TEAMS_WEBHOOK_FILE);
  if (!webhookUrl) return;

  const t = record.trigger || {};
  const color = (t.severity ?? 100) >= 75 ? "C4314B" : "E8A33D"; // red for high severity, amber otherwise
  const body = {
    "@type": "MessageCard",
    "@context": "http://schema.org/extensions",
    themeColor: color,
    summary: `Jarvis autopilot: ${t.symptom || "new finding"}`,
    sections: [{
      activityTitle: "Jarvis Autopilot Finding",
      activitySubtitle: t.entity || "",
      facts: [
        { name: "Category", value: t.category || "unknown" },
        { name: "Symptom", value: t.symptom || "" },
        { name: "Source", value: t.source || "" },
        { name: "Severity", value: t.severity != null ? String(t.severity) : "n/a" },
      ],
      text: (record.finding || "").slice(0, 3000),
    }],
  };

  try {
    const resp = await fetch(webhookUrl, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    if (!resp.ok) console.error(`[notifier] Teams webhook returned ${resp.status}`);
  } catch (e) {
    console.error("[notifier] Teams notification failed:", e.message);
  }
}

async function notifyEmail(record) {
  const apiKey = readSecretFile(RESEND_API_KEY_FILE);
  if (!apiKey || !EMAIL_FROM || EMAIL_TO.length === 0) return;

  const t = record.trigger || {};
  const subject = `Jarvis autopilot: ${t.symptom || "new finding"} (${t.entity || "lab network"})`;
  const text = `Category: ${t.category}\nEntity: ${t.entity}\nSeverity: ${t.severity ?? "n/a"}\nSource: ${t.source}\n\n${record.finding}`;

  try {
    const resp = await fetch("https://api.resend.com/emails", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": `Bearer ${apiKey}` },
      body: JSON.stringify({ from: EMAIL_FROM, to: EMAIL_TO, subject, text }),
    });
    if (!resp.ok) console.error(`[notifier] Resend API returned ${resp.status}: ${await resp.text()}`);
  } catch (e) {
    console.error("[notifier] Email notification failed:", e.message);
  }
}

// Fires every configured channel for one finding record. Each channel is
// independently a no-op if its secret file isn't present — nothing to
// configure to leave a channel off.
export async function notify(record) {
  if (!shouldNotify(record)) return;
  await Promise.allSettled([notifyTeams(record), notifyEmail(record)]);
}
