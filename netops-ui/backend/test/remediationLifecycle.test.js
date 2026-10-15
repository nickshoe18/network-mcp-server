import test from "node:test";
import assert from "node:assert/strict";
import { executeAndVerify, hasPreviousActionAttempt, preserveLatestActionState } from "../src/remediationLifecycle.js";

const action = { name: "reboot_ap", params: { device_id: "device-1" }, reason: "degraded device" };

test("does not run post-action checks after a failed execution", async () => {
  let verifyCalls = 0;
  const outcome = await executeAndVerify(
    action,
    async () => ({ ok: false, error: "device rejected action" }),
    async () => { verifyCalls += 1; return { status: "verified" }; },
  );
  assert.equal(outcome.status, "failed");
  assert.equal(outcome.result.error, "device rejected action");
  assert.equal(outcome.verification.status, "not_run");
  assert.equal(verifyCalls, 0);
});

test("records thrown execution errors without attempting a retry or verification", async () => {
  let executeCalls = 0;
  let verifyCalls = 0;
  const outcome = await executeAndVerify(
    action,
    async () => { executeCalls += 1; throw new Error("MCP timeout"); },
    async () => { verifyCalls += 1; return { status: "verified" }; },
  );
  assert.equal(outcome.status, "failed");
  assert.match(outcome.result.error, /MCP timeout/);
  assert.equal(executeCalls, 1);
  assert.equal(verifyCalls, 0);
});

test("verifies successful execution once and keeps inconclusive checks explicit", async () => {
  let executeCalls = 0;
  let verifyCalls = 0;
  const outcome = await executeAndVerify(
    action,
    async () => { executeCalls += 1; return { ok: true }; },
    async () => { verifyCalls += 1; return { status: "inconclusive", summary: "No fresh telemetry." }; },
  );
  assert.equal(outcome.status, "executed");
  assert.equal(executeCalls, 1);
  assert.equal(verifyCalls, 1);
  assert.equal(outcome.verification.status, "inconclusive");
});

test("records verification errors as inconclusive without changing execution success", async () => {
  const outcome = await executeAndVerify(
    action,
    async () => ({ ok: true }),
    async () => { throw new Error("MCP unavailable"); },
  );
  assert.equal(outcome.status, "executed");
  assert.equal(outcome.result.ok, true);
  assert.equal(outcome.verification.status, "inconclusive");
  assert.match(outcome.verification.summary, /MCP unavailable/);
});

test("prevents automatic retries after an action is executing or has finished", () => {
  assert.equal(hasPreviousActionAttempt([{ id: "alert-1", proposedAction: { status: "executing" } }], "alert-1"), true);
  assert.equal(hasPreviousActionAttempt([{ id: "alert-1", proposedAction: { status: "executed" } }], "alert-1"), true);
  assert.equal(hasPreviousActionAttempt([{ id: "alert-1", proposedAction: { status: "failed" } }], "alert-1"), true);
  assert.equal(hasPreviousActionAttempt([{ id: "alert-1", proposedAction: { status: "not_run" } }], "alert-1"), true);
  assert.equal(hasPreviousActionAttempt([{ id: "alert-1", proposedAction: { status: "pending" } }], "alert-1"), false);
  assert.equal(hasPreviousActionAttempt([], "alert-1"), false);
});

test("does not let a stale poll snapshot revert persisted action progress", () => {
  const stale = { id: "alert-1", timestamp: "2026-01-01T00:00:00.000Z", proposedAction: { status: "pending" } };
  const current = { ...stale, proposedAction: { status: "executed" }, actionDecision: { status: "executed" } };
  const merged = preserveLatestActionState(stale, current);
  assert.equal(merged.proposedAction.status, "executed");
  assert.equal(merged.actionDecision.status, "executed");
  assert.equal(preserveLatestActionState(current, { ...stale, proposedAction: { status: "executing" } }).proposedAction.status, "executed");
});
