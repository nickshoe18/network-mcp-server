import test from "node:test";
import assert from "node:assert/strict";
import { evaluateRemediation, REMEDIATION_CONFIDENCE_THRESHOLD } from "../src/remediationPolicy.js";

const deviceId = "00000000-0000-0000-1000-045c6c556ee2";
const siteId = "59f74351-5c94-49bf-adea-dc96f4b132bf";
const evidenceCapturedAt = new Date().toISOString();
const firstEvidence = `Device ${deviceId} is online and reachable.`;
const secondEvidence = `Device ${deviceId} radio remains degraded after the previous recovery check.`;
const investigation = `${firstEvidence}\n${secondEvidence}`;
const rebootProposal = {
  proposal: "reboot_ap",
  params: { site_id: siteId, device_id: deviceId },
  reason: "Reboot the online AP because its radio remains degraded.",
  confidence: 0.91,
  evidenceFor: [firstEvidence, secondEvidence],
  evidenceAgainst: [],
  evidenceCapturedAt,
};

test("allows an autonomous action only when confidence and deterministic checks pass", () => {
  const result = evaluateRemediation(rebootProposal, investigation, "marvis_actions", true);
  assert.equal(result.autonomousEligible, true);
  assert.equal(result.approvalEligible, true);
  assert.equal(result.threshold, REMEDIATION_CONFIDENCE_THRESHOLD);
  assert.ok(result.checks.every(check => check.passed));
});

test("requires human approval below the confidence floor", () => {
  const result = evaluateRemediation(
    { ...rebootProposal, confidence: REMEDIATION_CONFIDENCE_THRESHOLD - 0.01 },
    investigation,
    "marvis_actions",
    true,
  );
  assert.equal(result.autonomousEligible, false);
  assert.equal(result.approvalEligible, true);
  assert.equal(result.checks.find(check => check.name === "confidence_threshold").passed, false);
});

test("allows the exact confidence boundary", () => {
  const result = evaluateRemediation(
    { ...rebootProposal, confidence: REMEDIATION_CONFIDENCE_THRESHOLD },
    investigation,
    "marvis_actions",
    true,
  );
  assert.equal(result.autonomousEligible, true);
});

test("blocks a wrong platform, ungrounded target, or contradictory evidence", () => {
  assert.equal(evaluateRemediation(rebootProposal, investigation, "central_alerts", true).approvalEligible, false);
  assert.equal(
    evaluateRemediation({ ...rebootProposal, params: { ...rebootProposal.params, device_id: "00000000-0000-0000-1000-000000000000" } }, investigation, "marvis_actions", true).approvalEligible,
    false,
  );
  assert.equal(
    evaluateRemediation({ ...rebootProposal, evidenceAgainst: ["The device is actually healthy."] }, investigation, "marvis_actions", true).approvalEligible,
    false,
  );
  assert.equal(
    evaluateRemediation({ ...rebootProposal, proposal: "arbitrary_write" }, investigation, "marvis_actions", true).approvalEligible,
    false,
  );
  assert.equal(
    evaluateRemediation({ ...rebootProposal, evidenceFor: [firstEvidence, firstEvidence] }, investigation, "marvis_actions", true).approvalEligible,
    false,
  );
  const suffixMac = "aa:bb:cc:dd:ee:ff";
  const deviceOnlyEvidence = "Device identifier 00000000-0000-0000-1000-aabbccddeeff is online.";
  assert.equal(
    evaluateRemediation({
      ...rebootProposal,
      proposal: "disconnect_client",
      params: { site_id: siteId, client_mac: suffixMac },
      evidenceFor: [deviceOnlyEvidence, "Another device record reports normal operation."],
    }, `${deviceOnlyEvidence}\nAnother device record reports normal operation.`, "marvis_actions", true).approvalEligible,
    false,
  );
});

test("does not reboot an offline device", () => {
  const offline = "Device is offline and unreachable. The AP radio remains degraded after checks.";
  const proposal = {
    ...rebootProposal,
    reason: "The device is offline but still misbehaving; reboot it.",
    evidenceFor: ["Device is offline and unreachable.", "The AP radio remains degraded after checks."],
  };
  const result = evaluateRemediation(proposal, offline, "marvis_actions", true);
  assert.equal(result.autonomousEligible, false);
  assert.equal(result.approvalEligible, false);
});

test("blocks DHCP lease release unless it is one client on the known serving gateway and network", () => {
  const gatewayId = "00000000-0000-0000-1000-0c812665a868";
  const mac = "aa:bb:cc:dd:ee:ff";
  const dhcpText = `DHCP gateway ${gatewayId} serves Wireless_Users. Client ${mac} has a stale duplicate IP lease.`;
  const proposal = {
    proposal: "release_dhcp_lease",
    params: { site_id: siteId, device_id: gatewayId, macs: [mac], network: "Wireless_Users" },
    reason: "Release the one stale DHCP lease.",
    confidence: 0.9,
    evidenceFor: [`DHCP gateway ${gatewayId} serves Wireless_Users.`, `Client ${mac} has a stale duplicate IP lease.`],
    evidenceAgainst: [],
    evidenceCapturedAt,
  };
  assert.equal(evaluateRemediation(proposal, dhcpText, "marvis_actions", true).autonomousEligible, true);
  assert.equal(
    evaluateRemediation({ ...proposal, params: { ...proposal.params, macs: [mac, "11:22:33:44:55:66"] } }, dhcpText, "marvis_actions", true).approvalEligible,
    false,
  );
  assert.equal(
    evaluateRemediation({ ...proposal, params: { ...proposal.params, device_id: deviceId } }, dhcpText, "marvis_actions", true).approvalEligible,
    false,
  );
});

test("keeps the master switch as a hard execution gate", () => {
  const result = evaluateRemediation(rebootProposal, investigation, "marvis_actions", false);
  assert.equal(result.approvalEligible, true);
  assert.equal(result.autonomousEligible, false);
  assert.equal(result.checks.find(check => check.name === "remediation_enabled").passed, false);
});

test("permits a grounded Central reboot only for a reachable misbehaving device", () => {
  const serial = "CN26KNN2Z0";
  const secondCentralEvidence = `Device serial ${serial} remains unresponsive after recovery.`;
  const centralFinding = `Device serial ${serial} is online and reachable. ${secondCentralEvidence}`;
  const proposal = {
    proposal: "reboot_central_device",
    params: { device_family: "cx", serial_number: serial },
    reason: "Reboot the online switch because it remains unresponsive.",
    confidence: 0.9,
    evidenceFor: [`Device serial ${serial} is online and reachable.`, secondCentralEvidence],
    evidenceAgainst: [],
    evidenceCapturedAt,
  };
  assert.equal(evaluateRemediation(proposal, centralFinding, "central_alerts", true).autonomousEligible, true);
});

test("allows a grounded single-device locator action", () => {
  const finding = `Device ${deviceId} is visible in the Stark Tower inventory. Device ${deviceId} is on the correct site.`;
  const proposal = {
    proposal: "locate_led",
    params: { site_id: siteId, device_id: deviceId, enabled: true },
    reason: "Locate this device for physical identification.",
    confidence: 0.9,
    evidenceFor: [`Device ${deviceId} is visible in the Stark Tower inventory.`, `Device ${deviceId} is on the correct site.`],
    evidenceAgainst: [],
    evidenceCapturedAt,
  };
  assert.equal(evaluateRemediation(proposal, finding, "marvis_actions", true).autonomousEligible, true);
});

test("allows a grounded one-client disconnect on Central", () => {
  const serial = "CN26KNN2Z0";
  const mac = "aa:bb:cc:dd:ee:ff";
  const first = `Client MAC ${mac} on AP serial ${serial} is misbehaving in an auth loop.`;
  const second = `The client MAC ${mac} repeatedly fails authentication.`;
  const proposal = {
    proposal: "disconnect_central_client",
    params: { device_kind: "ap", serial_number: serial, mac },
    reason: "Disconnect one client stuck in an authentication loop.",
    confidence: 0.89,
    evidenceFor: [first, second],
    evidenceAgainst: [],
    evidenceCapturedAt,
  };
  assert.equal(evaluateRemediation(proposal, `${first}\n${second}`, "central_alerts", true).autonomousEligible, true);
});

test("blocks evidence older than the action freshness window", () => {
  const result = evaluateRemediation(
    { ...rebootProposal, evidenceCapturedAt: new Date(Date.now() - 6 * 60 * 1000).toISOString() },
    investigation,
    "marvis_actions",
    true,
  );
  assert.equal(result.autonomousEligible, false);
  assert.equal(result.approvalEligible, false);
  assert.equal(result.checks.find(check => check.name === "evidence_fresh").passed, false);
});
