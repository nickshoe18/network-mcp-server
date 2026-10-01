import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import { useFindings } from "../hooks/useFindings.js";

function relativeTime(iso) {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

const ACTION_LABELS = {
  reboot_ap: "Reboot AP",
  disconnect_client: "Disconnect client",
  locate_led: "Toggle locate LED",
};

const STATUS_STYLE = {
  pending: { color: "#E08A00", bg: "#E08A001a", label: "Awaiting approval" },
  executed: { color: "#1B8C6E", bg: "#1B8C6E1a", label: "Executed" },
  failed: { color: "#C4314B", bg: "#C4314B1a", label: "Failed" },
  declined: { color: "#666", bg: "#2a2d3a", label: "Declined" },
};

function ProposedAction({ findingId, action, onChanged }) {
  const [busy, setBusy] = useState(false);
  const style = STATUS_STYLE[action.status] || STATUS_STYLE.pending;

  const act = async (verb) => {
    setBusy(true);
    try {
      const res = await fetch(`/api/findings/${findingId}/${verb}`, { method: "POST" });
      const body = await res.json();
      if (!res.ok) throw new Error(body.error || `${verb} failed`);
    } catch (e) {
      // surfaced via the status badge on refetch either way — a toast isn't worth the weight here
      console.error(e);
    } finally {
      setBusy(false);
      onChanged();
    }
  };

  return (
    <div style={{ marginTop: 8, padding: "8px 10px", background: "#1a1e2a", border: `1px solid ${style.color}40`, borderRadius: 6 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: "#c8cad4" }}>Proposed: {ACTION_LABELS[action.name] || action.name}</span>
        <span style={{ fontSize: 9, color: style.color, background: style.bg, borderRadius: 10, padding: "1px 7px", textTransform: "uppercase", letterSpacing: ".04em" }}>{style.label}</span>
      </div>
      <div style={{ fontSize: 11, color: "#888", lineHeight: 1.4, marginBottom: action.status === "pending" ? 8 : 0 }}>{action.reason}</div>
      {action.status === "pending" && (
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={() => act("approve")} disabled={busy}
            style={{ flex: 1, padding: "5px 0", fontSize: 11, fontWeight: 600, borderRadius: 5, border: "none", background: "#1B8C6E", color: "#fff", cursor: busy ? "default" : "pointer", opacity: busy ? 0.6 : 1 }}>
            {busy ? "…" : "Approve"}
          </button>
          <button onClick={() => act("decline")} disabled={busy}
            style={{ flex: 1, padding: "5px 0", fontSize: 11, borderRadius: 5, border: "1px solid #2a2d3a", background: "none", color: "#888", cursor: busy ? "default" : "pointer", opacity: busy ? 0.6 : 1 }}>
            Decline
          </button>
        </div>
      )}
      {action.status === "failed" && action.result?.error && (
        <div style={{ fontSize: 10, color: "#C4314B", marginTop: 4 }}>{action.result.error}</div>
      )}
    </div>
  );
}

function FindingRow({ item, onChanged }) {
  const [open, setOpen] = useState(false);
  const t = item.trigger || {};
  return (
    <div style={{ borderBottom: "1px solid #22242e", padding: "8px 0" }}>
      <button onClick={() => setOpen(o => !o)}
        style={{ width: "100%", textAlign: "left", background: "none", border: "none", cursor: "pointer", padding: 0, display: "flex", flexDirection: "column", gap: 2 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 6 }}>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#c8cad4", textTransform: "capitalize" }}>{t.category || "issue"}</span>
          <span style={{ fontSize: 10, color: "#555", flexShrink: 0 }}>{relativeTime(item.timestamp)}</span>
        </div>
        <div style={{ fontSize: 11, color: "#888", lineHeight: 1.4 }}>{t.symptom}{t.entity ? ` — ${t.entity}` : ""}</div>
      </button>
      {item.proposedAction?.status === "pending" && !open && (
        <div style={{ fontSize: 10, color: "#E08A00", marginTop: 4 }}>⚠ Proposed action awaiting approval — expand for details</div>
      )}
      {open && (
        <div style={{ marginTop: 8, padding: "8px 10px", background: "#12141c", border: "1px solid #2a2d3a", borderRadius: 6, fontSize: 11, color: "#a8aab4", maxHeight: 320, overflowY: "auto" }}>
          <div className="md-body"><ReactMarkdown>{item.finding || "(no finding text)"}</ReactMarkdown></div>
          {item.toolLog?.length > 0 && (
            <div style={{ marginTop: 8, paddingTop: 8, borderTop: "1px solid #2a2d3a", fontSize: 10, color: "#555" }}>
              Checked: {item.toolLog.join(", ")}
            </div>
          )}
          {item.proposedAction && <ProposedAction findingId={item.id} action={item.proposedAction} onChanged={onChanged} />}
        </div>
      )}
    </div>
  );
}

export function FindingsPanel() {
  const { findings, loading, refetch } = useFindings();
  return (
    <div style={{ padding: "12px 12px 4px" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#555", letterSpacing: ".08em", textTransform: "uppercase" }}>Autonomous findings</div>
        {findings.length > 0 && (
          <span style={{ fontSize: 10, color: "#1B8C6E", background: "#1B8C6E1a", borderRadius: 10, padding: "1px 7px" }}>{findings.length}</span>
        )}
      </div>
      {loading ? (
        <div style={{ fontSize: 11, color: "#555", padding: "4px 0" }}>Loading…</div>
      ) : findings.length === 0 ? (
        <div style={{ fontSize: 11, color: "#444", padding: "4px 0", lineHeight: 1.5 }}>Jarvis is watching Marvis Actions. Nothing new to report yet.</div>
      ) : (
        <div>{findings.slice(0, 8).map(item => <FindingRow key={item.id + item.timestamp} item={item} onChanged={refetch} />)}</div>
      )}
    </div>
  );
}
