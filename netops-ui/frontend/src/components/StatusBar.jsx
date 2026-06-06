import React from "react";
const STATUS_COLOR = { ok: "#1B8C6E", degraded: "#E08A00", unknown: "#888" };
export function StatusBar({ platforms, loading }) {
  const connected = platforms.filter(p => p.status === "ok").length;
  const total = platforms.length;
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 20px", height: 44, background: "#161820", borderBottom: "1px solid #2a2d3a", flexShrink: 0 }}>
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div style={{ width: 8, height: 8, borderRadius: "50%", background: connected === total ? "#1B8C6E" : "#E08A00", boxShadow: `0 0 8px ${connected === total ? "#1B8C6E" : "#E08A00"}80` }} />
        <span style={{ fontSize: 13, fontWeight: 600, color: "#e8eaf0" }}>HPE Network Ops</span>
      </div>
      <div style={{ display: "flex", gap: 16, alignItems: "center" }}>
        {!loading && <span style={{ fontSize: 12, color: "#555" }}>{connected}/{total} platforms connected · 1,034 tools</span>}
        {platforms.map(p => (
          <div key={p.key} style={{ width: 6, height: 6, borderRadius: "50%", background: STATUS_COLOR[p.status] ?? "#888" }} title={p.label} />
        ))}
      </div>
    </div>
  );
}
