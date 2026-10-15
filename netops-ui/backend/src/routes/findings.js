import { Router } from "express";
import { getFindings, updateFinding } from "../poller.js";
import { executeRemediation, remediationEnabled } from "../remediation.js";
import { verifyRemediation } from "../jarvisAgent.js";
import { evaluateRemediation, REMEDIATION_EVIDENCE_MAX_AGE_MS } from "../remediationPolicy.js";
import { executeAndVerify } from "../remediationLifecycle.js";

export const findingsRouter = Router();
const MAX_PROPOSAL_AGE_MS = REMEDIATION_EVIDENCE_MAX_AGE_MS;

findingsRouter.get("/", (_req, res) => {
  res.json({ ok: true, data: getFindings() });
});

// Human approval is still available for otherwise-safe proposals below the
// autonomous confidence threshold. Autonomous actions are executed by poller.js
// through the same fixed action wrappers.
findingsRouter.post("/:id/approve", async (req, res) => {
  const { id } = req.params;
  const finding = getFindings().find(f => f.id === id);
  if (!finding) return res.status(404).json({ ok: false, error: "finding not found" });

  const proposal = finding.proposedAction;
  if (!proposal) return res.status(400).json({ ok: false, error: "this finding has no proposed action" });
  if (proposal.status !== "pending") return res.status(409).json({ ok: false, error: `already ${proposal.status}` });
  if (!remediationEnabled()) return res.status(403).json({ ok: false, error: "remediation disabled (JARVIS_REMEDIATION_ENABLED != true) — nothing will execute" });

  const createdAt = Date.parse(proposal.createdAt || finding.timestamp);
  if (!Number.isFinite(createdAt) || Date.now() - createdAt > MAX_PROPOSAL_AGE_MS) {
    updateFinding(id, f => {
      f.proposedAction.status = "stale";
      f.proposedAction.staleAt = new Date().toISOString();
      f.actionDecision = { status: "stale", reason: "Evidence is older than five minutes; investigate again before acting." };
    });
    return res.status(409).json({ ok: false, error: "proposal is stale; investigate again before acting" });
  }

  const decision = {
    proposal: proposal.name,
    params: proposal.params,
    reason: proposal.reason,
    confidence: proposal.confidence,
    evidenceFor: proposal.evidenceFor,
    evidenceAgainst: proposal.evidenceAgainst,
    evidenceCapturedAt: proposal.evidenceCapturedAt,
  };
  const eligibility = evaluateRemediation(decision, (proposal.evidenceFor || []).join("\n"), finding.trigger?.source, true);
  if (!eligibility.approvalEligible) {
    updateFinding(id, f => {
      f.proposedAction.status = "blocked";
      f.proposedAction.eligibility = eligibility;
      f.actionDecision = { status: "blocked", reason: eligibility.reason, checks: eligibility.checks };
    });
    return res.status(409).json({ ok: false, error: "mandatory safety checks failed; action was not run", data: eligibility });
  }

  let claimed = false;
  updateFinding(id, f => {
    if (f.proposedAction?.status !== "pending") return;
    f.proposedAction.status = "executing";
    f.proposedAction.executionMode = "human_approval";
    f.proposedAction.executionStartedAt = new Date().toISOString();
    f.proposedAction.eligibility = eligibility;
    f.actionDecision = { status: "executing", reason: "Human approved the pending action.", checks: eligibility.checks };
    claimed = true;
  });
  if (!claimed) return res.status(409).json({ ok: false, error: "action is no longer pending" });

  const outcome = await executeAndVerify(
    { name: proposal.name, params: proposal.params || {}, reason: proposal.reason },
    executeRemediation,
    verifyRemediation,
  );

  const updated = updateFinding(id, f => {
    f.proposedAction.status = outcome.status;
    f.proposedAction.approvedAt = new Date().toISOString();
    f.proposedAction.result = outcome.result;
    f.proposedAction.verification = outcome.verification;
    f.actionDecision = {
      status: f.proposedAction.status,
      reason: outcome.status === "executed" ? "Human-approved action completed." : "Human-approved action failed.",
      checks: eligibility.checks,
    };
  });

  res.json({ ok: outcome.status === "executed", data: updated?.proposedAction });
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
    f.actionDecision = { status: "declined", reason: "Human declined the proposed action." };
  });
  res.json({ ok: true, data: updated?.proposedAction });
});
