import React from "react";

const QUICK_ACTIONS = [
  { label: "Network health overview",  prompt: "Run a full network health overview across all platforms" },
  { label: "Active alerts",            prompt: "Show all active alerts across Aruba Central and Juniper Mist" },
  { label: "Offline APs",             prompt: "List all offline APs in my Mist organisation" },
  { label: "ClearPass sessions",       prompt: "Show active ClearPass authentication sessions" },
  { label: "UXI sensor status",        prompt: "List all UXI sensors and their current test results" },
  { label: "GreenLake subscriptions",  prompt: "Show my HPE GreenLake workspace subscriptions" },
];

const STATUS_COLOR = { ok: "#1B8C6E", degraded: "#E08A00", unknown: "#888" };

export function Sidebar({ platforms, loading, onAction }) {
  return (
    <aside style={{ width: 240, flexShrink: 0, background: "#161820", borderRight: "1px solid #2a2d3a", display: "flex", flexDirection: "column", overflow: "hidden" }}>
      <div style={{ padding: "16px 16px 12px", borderBottom: "1px solid #2a2d3a", display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 28, height: 28, borderRadius: 6, background: "linear-gradient(135deg,#1B4F8A,#1B8C6E)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, color: "#fff", fontWeight: 700 }}>H</div>
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: "#e8eaf0" }}>HPE Network Ops</div>
          <div style={{ fontSize: 11, color: "#555" }}>AI Operations Centre</div>
        </div>
      </div>

      <div style={{ padding: "12px 12px 0" }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#555", letterSpacing: ".08em", marginBottom: 8, textTransform: "uppercase" }}>Platforms</div>
        {loading ? <div style={{ fontSize: 12, color: "#555", padding: "8px 0" }}>Connecting…</div> : platforms.map(p => (
          <div key={p.key} style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "6px 8px", borderRadius: 6, marginBottom: 2 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%", background: STATUS_COLOR[p.status] ?? "#888", flexShrink: 0, boxShadow: p.status === "ok" ? `0 0 6px ${STATUS_COLOR.ok}80` : "none" }} />
              <span style={{ fontSize: 12, color: p.status === "ok" ? "#c8cad4" : "#666" }}>{p.label}</span>
            </div>
          </div>
        ))}
      </div>

      <div style={{ padding: "12px", borderTop: "1px solid #2a2d3a", marginTop: "auto" }}>
        <div style={{ fontSize: 10, fontWeight: 600, color: "#555", letterSpacing: ".08em", marginBottom: 8, textTransform: "uppercase" }}>Quick actions</div>
        {QUICK_ACTIONS.map(({ label, prompt }) => (
          <button key={label} onClick={() => onAction(prompt)}
            style={{ width: "100%", textAlign: "left", padding: "6px 8px", marginBottom: 3, background: "none", border: "1px solid #2a2d3a", borderRadius: 6, fontSize: 11, color: "#888", cursor: "pointer" }}
            onMouseEnter={e => { e.target.style.background = "#1e2030"; e.target.style.color = "#c8cad4"; }}
            onMouseLeave={e => { e.target.style.background = "none"; e.target.style.color = "#888"; }}>
            {label} ↗
          </button>
        ))}
      </div>
    </aside>
  );
}
