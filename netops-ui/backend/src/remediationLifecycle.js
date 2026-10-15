const ACTION_STATUS_RANK = {
  pending: 1,
  executing: 2,
  executed: 3,
  failed: 3,
  declined: 3,
  blocked: 3,
  disabled: 3,
  stale: 3,
  not_run: 3,
};

export function hasPreviousActionAttempt(findings, findingId) {
  return findings.some(finding => finding.id === findingId
    && ["executing", "executed", "failed", "not_run"].includes(finding.proposedAction?.status));
}

export function preserveLatestActionState(incoming, persisted) {
  const currentRank = ACTION_STATUS_RANK[persisted?.proposedAction?.status] || 0;
  const incomingRank = ACTION_STATUS_RANK[incoming?.proposedAction?.status] || 0;
  if (currentRank === 0 || currentRank < incomingRank) return incoming;
  return {
    ...incoming,
    proposedAction: persisted.proposedAction,
    actionDecision: persisted.actionDecision || incoming.actionDecision,
  };
}

export async function executeAndVerify(action, execute, verify) {
  let result;
  try {
    result = await execute(action.name, action.params);
  } catch (error) {
    result = { ok: false, error: error.message };
  }

  if (!result?.ok) {
    return {
      status: "failed",
      result: result || { ok: false, error: "action returned no result" },
      verification: {
        status: "not_run",
        summary: "The action failed; no post-action verification was run.",
        evidence: [],
        toolLog: [],
      },
    };
  }

  let verification;
  try {
    verification = await verify(action.name, action.params, action.reason);
  } catch (error) {
    verification = {
      status: "inconclusive",
      summary: `Post-action verification failed: ${error.message}`,
      evidence: [],
      toolLog: [],
    };
  }
  return { status: "executed", result, verification };
}
