import { Router } from "express";
import { getFindings, updateFinding } from "../poller.js";
import { rebootAp, disconnectClient, setLocateLed, remediationEnabled } from "../remediation.js";

export const findingsRouter = Router();

findingsRouter.get("/", (_req, res) => {
  res.json({ ok: true, data: getFindings() });
});

// The ONLY route in this whole system that can cause a write to actually happen —
// and only when a real human sends this request (a UI button click). The LLM never
// calls this; proposeRemediation() in jarvisAgent.js only ever proposes and stores,
// it has no reference to this route or to remediation.js's execute functions.
findingsRouter.post("/:id/approve", async (req, res) => {
  const { id } = req.params;
  const finding = getFindings().find(f => f.id === id);
  if (!finding) return res.status(404).json({ ok: false, error: "finding not found" });

  const proposal = finding.proposedAction;
  if (!proposal) return res.status(400).json({ ok: false, error: "this finding has no proposed action" });
  if (proposal.status !== "pending") return res.status(409).json({ ok: false, error: `already ${proposal.status}` });
  if (!remediationEnabled()) return res.status(403).json({ ok: false, error: "remediation disabled (JARVIS_REMEDIATION_ENABLED != true) — nothing will execute" });

  const p = proposal.params || {};
  let result;
  try {
    if (proposal.name === "reboot_ap") result = await rebootAp(p.site_id, p.device_id);
    else if (proposal.name === "disconnect_client") result = await disconnectClient(p.site_id, p.client_mac);
    else if (proposal.name === "locate_led") result = await setLocateLed(p.site_id, p.device_id, p.enabled);
    else return res.status(400).json({ ok: false, error: `unknown action ${proposal.name}` });
  } catch (e) {
    result = { ok: false, error: e.message };
  }

  const updated = updateFinding(id, f => {
    f.proposedAction.status = result.ok ? "executed" : "failed";
    f.proposedAction.approvedAt = new Date().toISOString();
    f.proposedAction.result = result;
  });

  res.json({ ok: result.ok, data: updated?.proposedAction });
});

// Explicit decline — leaves the proposal visible but closed, distinct from "pending".
findingsRouter.post("/:id/decline", (req, res) => {
  const { id } = req.params;
  const finding = getFindings().find(f => f.id === id);
  if (!finding) return res.status(404).json({ ok: false, error: "finding not found" });
  if (!finding.proposedAction) return res.status(400).json({ ok: false, error: "this finding has no proposed action" });
  if (finding.proposedAction.status !== "pending") return res.status(409).json({ ok: false, error: `already ${finding.proposedAction.status}` });

  const updated = updateFinding(id, f => {
    f.proposedAction.status = "declined";
    f.proposedAction.approvedAt = new Date().toISOString();
  });
  res.json({ ok: true, data: updated?.proposedAction });
});
