export const REMEDIATION_CONFIDENCE_THRESHOLD = 0.85;
export const REMEDIATION_EVIDENCE_MAX_AGE_MS = 5 * 60 * 1000;

const ACTION_PLATFORM = {
  reboot_ap: "mist",
  disconnect_client: "mist",
  locate_led: "mist",
  release_dhcp_lease: "mist",
  reboot_central_device: "central",
  disconnect_central_client: "central",
  locate_central_device: "central",
};

const TARGET_FIELDS = {
  reboot_ap: ["device_id"],
  disconnect_client: ["client_mac"],
  locate_led: ["device_id"],
  release_dhcp_lease: ["device_id", "macs", "network"],
  reboot_central_device: ["serial_number"],
  disconnect_central_client: ["serial_number", "mac"],
  locate_central_device: ["serial_number"],
};

const DEVICE_ID = /^00000000-0000-0000-1000-[0-9a-f]{12}$/i;
const MAC = /^(?:[0-9a-f]{2}[:-]?){5}[0-9a-f]{2}$/i;
const LAB_MIST_SITE_ID = process.env.MIST_SITE_ID || "59f74351-5c94-49bf-adea-dc96f4b132bf";
const LAB_DHCP_GATEWAY_ID = "00000000-0000-0000-1000-0c812665a868";

function containsExact(text, value) {
  return typeof value === "string" && value.length > 0 && text.toLowerCase().includes(value.toLowerCase());
}

function containsMac(text, mac) {
  const octets = mac.match(/[0-9a-f]{2}/gi);
  if (!octets || octets.length !== 6) return false;
  const pattern = new RegExp(`(?<![0-9a-f])${octets.join("[\\s:-]?")}(?![0-9a-f])`, "gi");
  return [...text.matchAll(pattern)].some(match => {
    const context = text.slice(Math.max(0, match.index - 80), match.index);
    return /\bclient\b|mac/i.test(context);
  });
}

function actionPreconditions(action, params, evidenceFor, reason) {
  const snippets = Array.isArray(evidenceFor) ? evidenceFor.filter(item => typeof item === "string") : [];
  const hasTarget = (snippet, target) => {
    if (typeof target !== "string" || !target) return false;
    if (target === params.device_id || target === params.serial_number) return containsExact(snippet, target);
    return containsMac(snippet, target);
  };
  const hasEvidence = (target, pattern) => snippets.some(snippet => hasTarget(snippet, target) && pattern.test(snippet));
  if (action === "reboot_central_device" && !["aos-s", "aps", "cx", "gateways"].includes(params.device_family)) return false;
  if (action === "disconnect_central_client") {
    if (!["ap", "switch", "gateway"].includes(params.device_kind)) return false;
    if (params.device_kind === "switch" && !["aos-s", "cx"].includes(params.switch_type)) return false;
    if (params.device_kind !== "switch" && params.switch_type !== undefined) return false;
  }
  if (action === "locate_central_device" && !["aos-s", "aps", "cx"].includes(params.device_family)) return false;
  if (["reboot_ap", "disconnect_client", "locate_led", "release_dhcp_lease"].includes(action)
    && params.site_id !== LAB_MIST_SITE_ID) return false;
  if (action === "locate_led" && params.enabled !== true) return false;
  if (action === "release_dhcp_lease" && params.device_id !== LAB_DHCP_GATEWAY_ID) return false;
  if (action === "reboot_ap" || action === "reboot_central_device") {
    const target = action === "reboot_ap" ? params.device_id : params.serial_number;
    return hasEvidence(target, /\b(?:online|reachable|connected)\b/i)
      && hasEvidence(target, /\b(?:misbehav|wedged|stuck|degraded|unresponsive|repeatedly failing)\w*/i);
  }
  if (action === "disconnect_client" || action === "disconnect_central_client") {
    const target = action === "disconnect_client" ? params.client_mac : params.mac;
    return hasEvidence(target, /\b(?:misbehav|stuck|failing|repeatedly disconnect|auth loop|roaming loop|bad session)\w*/i);
  }
  if (action === "locate_led" || action === "locate_central_device") {
    return /\b(?:locate|identify|find|physical)\b/.test(reason.toLowerCase());
  }
  if (action === "release_dhcp_lease") {
    const client = params.macs?.[0];
    return typeof params.network === "string"
      && snippets.some(snippet => hasTarget(snippet, params.device_id)
        && containsExact(snippet, params.network)
        && /\b(?:dhcp|lease)\b/i.test(snippet)
        && /\b(?:gateway|dhcp server)\b/i.test(snippet))
      && hasEvidence(client, /\b(?:stale|duplicate|wrong subnet|apipa|no ip|bad lease)\b/i);
  }
  return false;
}

function evidenceIsGrounded(evidence, text) {
  return Array.isArray(evidence)
    && evidence.length >= 2
    && new Set(evidence.map(item => typeof item === "string" ? item.trim() : "")).size >= 2
    && evidence.every(item => typeof item === "string" && item.trim().length >= 12 && text.includes(item.trim()));
}

export function evaluateRemediation(proposal, investigationText, triggerSource, isEnabled) {
  const action = proposal?.proposal;
  const params = proposal?.params || {};
  const confidence = proposal?.confidence;
  const reason = typeof proposal?.reason === "string" ? proposal.reason : "";
  const text = String(investigationText || "");
  const expectedPlatform = ACTION_PLATFORM[action];
  const sourcePlatform = triggerSource === "marvis_actions" ? "mist"
    : triggerSource === "central_alerts" ? "central" : null;
  const evidence = Array.isArray(proposal?.evidenceFor)
    ? proposal.evidenceFor.filter(item => typeof item === "string").map(item => item.trim()).join("\n")
    : "";
  const identityFields = TARGET_FIELDS[action] || [];
  const targetPresent = identityFields.length > 0
    && identityFields.every(field => {
      const value = params[field];
      if (Array.isArray(value)) return value.length === 1 && value.every(item => MAC.test(item) && containsMac(evidence, item));
      if (field === "network") return typeof value === "string" && containsExact(evidence, value);
      if (field === "device_id") return DEVICE_ID.test(value || "") && containsExact(evidence, value);
      if (field === "client_mac" || field === "mac") return MAC.test(value || "") && containsMac(evidence, value);
      return typeof value === "string" && value.length > 0 && containsExact(evidence, value);
    });
  const groundedEvidence = evidenceIsGrounded(proposal?.evidenceFor, text);
  const noContradictoryEvidence = Array.isArray(proposal?.evidenceAgainst) && proposal.evidenceAgainst.length === 0;
  const preconditionsMet = actionPreconditions(action, params, proposal?.evidenceFor, reason);
  const capturedAt = Date.parse(proposal?.evidenceCapturedAt || "");
  const evidenceFresh = Number.isFinite(capturedAt)
    && capturedAt <= Date.now()
    && Date.now() - capturedAt <= REMEDIATION_EVIDENCE_MAX_AGE_MS;
  const confidenceMet = Number.isFinite(confidence)
    && confidence >= REMEDIATION_CONFIDENCE_THRESHOLD
    && confidence <= 1;

  const checks = [
    { name: "allowlisted_action", passed: Boolean(expectedPlatform) },
    { name: "source_platform_match", passed: Boolean(expectedPlatform && sourcePlatform === expectedPlatform) },
    { name: "exact_target_in_evidence", passed: targetPresent },
    { name: "grounded_supporting_evidence", passed: groundedEvidence },
    { name: "evidence_fresh", passed: evidenceFresh, maxAgeMs: REMEDIATION_EVIDENCE_MAX_AGE_MS },
    { name: "no_reported_contradictory_evidence", passed: noContradictoryEvidence },
    { name: "action_preconditions", passed: preconditionsMet },
    { name: "confidence_threshold", passed: confidenceMet, threshold: REMEDIATION_CONFIDENCE_THRESHOLD },
  ];
  const approvalEligible = checks.slice(0, 7).every(check => check.passed);
  const autonomousEligible = approvalEligible && confidenceMet && isEnabled === true;
  if (isEnabled !== true) {
    checks.push({ name: "remediation_enabled", passed: false });
  } else {
    checks.push({ name: "remediation_enabled", passed: true });
  }

  return {
    approvalEligible,
    autonomousEligible,
    confidence: Number.isFinite(confidence) ? confidence : null,
    threshold: REMEDIATION_CONFIDENCE_THRESHOLD,
    checks,
    reason: autonomousEligible
      ? "All confidence and safety checks passed."
      : !approvalEligible
        ? "One or more mandatory safety checks failed; do not execute."
        : !confidenceMet
          ? "Confidence is below the autonomous execution threshold; human approval is required."
          : "Autonomous remediation is disabled; human approval cannot execute while the master switch is off.",
  };
}
