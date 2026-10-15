import Anthropic from "@anthropic-ai/sdk";
import { JARVIS_SYSTEM, JARVIS_TOOLS, JARVIS_MODEL, readRunbook, checkReadOnly } from "./jarvis.js";
import { initSession, mcpCall } from "./routes/chat.js";
import { cachedSystem, cachedTools, withCacheBreakpoint } from "./anthropicCache.js";
import { REMEDIATION_EVIDENCE_MAX_AGE_MS } from "./remediationPolicy.js";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MAX_TURNS = 15;
const MAX_EVIDENCE_CHARS = 50000;

// Runs one self-contained, read-only Jarvis investigation to completion and returns
// the final answer text plus a log of what it looked at. Used by the autopilot
// poller (poller.js) — no streaming, no user in the loop, same read-only gate
// (checkReadOnly) as the interactive Jarvis chat mode uses.
export async function runJarvisInvestigation(promptText) {
  const sessionId = await initSession();
  let messages = [{ role: "user", content: promptText }];
  const toolLog = [];
  const observedEvidence = [];
  let evidenceChars = 0;
  let evidenceCapturedAt = null;

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const response = await client.messages.create({
      model: JARVIS_MODEL,
      max_tokens: 8192,
      system: cachedSystem(JARVIS_SYSTEM),
      messages: withCacheBreakpoint(messages),
      tools: cachedTools(JARVIS_TOOLS),
    });

    if (response.stop_reason !== "tool_use") {
      const text = response.content.filter(b => b.type === "text").map(b => b.text).join("\n").trim();
      return { text, toolLog, observedEvidence, evidenceCapturedAt };
    }

    const toolUseBlocks = response.content.filter(b => b.type === "tool_use");
    const toolResults = [];

    for (const toolUse of toolUseBlocks) {
      const label = toolUse.input.description || (toolUse.name === "read_runbook" ? "runbook: " + (toolUse.input.name || "list") : toolUse.name);
      toolLog.push(label);
      let resultText;
      try {
        if (toolUse.name === "read_runbook") {
          resultText = readRunbook(toolUse.input.name);
        } else {
          const blocked = checkReadOnly(toolUse.input.code || "");
          if (blocked) {
            toolResults.push({ type: "tool_result", tool_use_id: toolUse.id, content: [{ type: "text", text: blocked }], is_error: true });
            continue;
          }
          const result = await mcpCall(sessionId, "tools/call", { name: "execute", arguments: { code: toolUse.input.code } });
          resultText = result?.content?.[0]?.text || JSON.stringify(result);
          const remaining = MAX_EVIDENCE_CHARS - evidenceChars;
          if (result && !result.isError && remaining > 0) {
            const excerpt = resultText.slice(0, remaining);
            observedEvidence.push(excerpt);
            evidenceChars += excerpt.length;
            if (excerpt && evidenceCapturedAt === null) evidenceCapturedAt = new Date().toISOString();
          }
        }
        toolResults.push({ type: "tool_result", tool_use_id: toolUse.id, content: [{ type: "text", text: resultText }] });
      } catch (e) {
        toolResults.push({ type: "tool_result", tool_use_id: toolUse.id, content: [{ type: "text", text: "Error: " + e.message }], is_error: true });
      }
    }

    messages = [...messages, { role: "assistant", content: response.content }, { role: "user", content: toolResults }];
  }

  return {
    text: "(investigation did not conclude within the turn limit — see tool log)",
    toolLog,
    observedEvidence,
    evidenceCapturedAt,
  };
}

// ── Stage 2: structured remediation decision ──────────────────────────────────
// This model call can only select a fixed action proposal. The deterministic policy
// and fixed backend wrappers decide whether it may execute.

const DECISION_FIELDS = {
  confidence: { type: "number", minimum: 0, maximum: 1, description: "Calibrated confidence that this diagnosis and action fit the evidence, from 0 to 1" },
  evidence_for: { type: "array", minItems: 2, items: { type: "string" }, description: "At least two distinct, exact evidence snippets copied from the direct read-only tool output" },
  evidence_against: { type: "array", items: { type: "string" }, description: "Exact evidence snippets that contradict this diagnosis; use an empty array when none were found" },
};

function actionSchema(properties, required) {
  return {
    type: "object",
    properties: { ...properties, ...DECISION_FIELDS },
    required: [...required, "confidence", "evidence_for", "evidence_against"],
  };
}

const REMEDIATION_PROPOSAL_TOOLS = [
  {
    name: "reboot_ap",
    description: "Reboot one AP that is online but wedged/misbehaving (bad radio/software state). Do NOT propose this for an AP with no connectivity at all — a cloud-issued reboot command cannot reach a fully disconnected device.",
    input_schema: actionSchema({
        site_id: { type: "string" }, device_id: { type: "string", description: "Mist device id, format 00000000-0000-0000-1000-<mac>" },
        reason: { type: "string", description: "One sentence: why this would be safe and is warranted" },
      }, ["site_id", "device_id", "reason"]),
  },
  {
    name: "disconnect_client",
    description: "Disconnect one specific misbehaving wireless client. It will likely reconnect on its own — this is a nudge, not a ban.",
    input_schema: actionSchema({ site_id: { type: "string" }, client_mac: { type: "string" }, reason: { type: "string" } }, ["site_id", "client_mac", "reason"]),
  },
  {
    name: "locate_led",
    description: "Start or stop blinking one device's LED for physical identification. Purely cosmetic — never fixes anything, only aids an on-site human.",
    input_schema: actionSchema({ site_id: { type: "string" }, device_id: { type: "string" }, enabled: { type: "boolean" }, reason: { type: "string" } }, ["site_id", "device_id", "enabled", "reason"]),
  },
  {
    name: "release_dhcp_lease",
    description: "Release one client's DHCP lease(s) by MAC on a specific DHCP network, forcing it to re-DHCP. Use for a stale/bad lease symptom — duplicate IP, wrong subnet, APIPA/no IP. device_id MUST be the gateway device that actually serves DHCP for that network (the LabSRX gateway in the lab), never the client's own id or an AP's id — releasing on the wrong device is a no-op at best.",
    input_schema: actionSchema({
        site_id: { type: "string" },
        device_id: { type: "string", description: "The gateway device serving DHCP for this network, format 00000000-0000-0000-1000-<mac>" },
        macs: { type: "array", items: { type: "string" }, description: "Client MAC address(es) whose lease(s) to release — colons or no colons, as they literally appear in the investigation" },
        network: { type: "string", description: "DHCP network/VLAN name the client is on, e.g. Wireless_Users" },
        reason: { type: "string" },
      }, ["site_id", "device_id", "macs", "network", "reason"]),
  },
  {
    name: "reboot_central_device",
    description: "Reboot one Aruba Central-managed device (AP, switch, or gateway) that's online but misbehaving. Do NOT propose this for a fully offline/unreachable device — a cloud reboot command can't reach it. Only use for Central-sourced findings.",
    input_schema: actionSchema({
        device_family: { type: "string", enum: ["aos-s", "aps", "cx", "gateways"], description: "aos-s/cx = switch, aps = AP, gateways = gateway" },
        serial_number: { type: "string" }, reason: { type: "string" },
      }, ["device_family", "serial_number", "reason"]),
  },
  {
    name: "disconnect_central_client",
    description: "Disconnect one misbehaving wireless or wired client from the Central-managed device it's on. A nudge, not a ban — it will likely reconnect on its own. Only use for Central-sourced findings.",
    input_schema: actionSchema({
        device_kind: { type: "string", enum: ["ap", "switch", "gateway"] },
        serial_number: { type: "string" },
        mac: { type: "string" },
        switch_type: { type: "string", enum: ["aos-s", "cx"], description: "Required only when device_kind is 'switch'" },
        reason: { type: "string" },
      }, ["device_kind", "serial_number", "mac", "reason"]),
  },
  {
    name: "locate_central_device",
    description: "Blink one Central-managed AP or switch's locator LED for physical identification. Purely cosmetic. Not available on gateways. Only use for Central-sourced findings.",
    input_schema: actionSchema({ device_family: { type: "string", enum: ["aos-s", "aps", "cx"] }, serial_number: { type: "string" }, reason: { type: "string" } }, ["device_family", "serial_number", "reason"]),
  },
  {
    name: "no_action",
    description: "None of the above is clearly a good idea for this specific issue, OR the target entity isn't confidently and exactly identified from the investigation. Use this whenever in doubt.",
    input_schema: { type: "object", properties: { reason: { type: "string" } }, required: ["reason"] },
  },
];

const REMEDIATION_PROPOSAL_SYSTEM = JARVIS_SYSTEM + `

You are making a structured action decision after a read-only investigation. You cannot execute anything. The finding and trigger source (marvis_actions = Mist, central_alerts = Central) are supplied. Choose at most one of these exact actions, only using target ids/MACs/serials/network names literally present in the finding: Mist: reboot_ap, disconnect_client, locate_led, release_dhcp_lease; Central: reboot_central_device, disconnect_central_client, locate_central_device. Never cross platforms or invent a target. DHCP release is only for a stale/bad lease symptom and requires the exact DHCP-serving gateway, one client MAC, and network in the evidence. Reboot only a device shown online/reachable and misbehaving. Include confidence, at least two exact evidence quotes, and an empty evidence_against array only if no meaningful contradictory evidence was found. Any uncertain diagnosis, conflicting evidence, or unsupported target means call no_action. Call exactly one tool. The backend independently evaluates your decision; a high confidence number alone never authorizes execution.`;

export async function proposeRemediation(investigationText, triggerSummary, observedEvidence = [], evidenceCapturedAt = null) {
  const sourceEvidence = observedEvidence.join("\n\n");
  const response = await client.messages.create({
    model: JARVIS_MODEL,
    max_tokens: 1024,
    system: cachedSystem(REMEDIATION_PROPOSAL_SYSTEM),
    messages: [{
      role: "user",
      content: `Trigger: ${triggerSummary}\n\nInvestigation finding:\n\n${investigationText}\n\n` +
        `Direct read-only tool evidence (quote supporting evidence exactly from this section):\n\n${sourceEvidence}`,
    }],
    tools: cachedTools(REMEDIATION_PROPOSAL_TOOLS),
    tool_choice: { type: "any" },
  });

  const toolUse = response.content.find(b => b.type === "tool_use");
  if (!toolUse || toolUse.name === "no_action") {
    return {
      proposal: "no_action",
      reason: toolUse?.input?.reason || "model did not call a tool (unexpected)",
      confidence: toolUse?.input?.confidence ?? null,
      evidenceCapturedAt,
    };
  }
  const {
    confidence,
    evidence_for: evidenceFor,
    evidence_against: evidenceAgainst,
    reason,
    ...params
  } = toolUse.input;
  return { proposal: toolUse.name, params, reason, confidence, evidenceFor, evidenceAgainst, evidenceCapturedAt };
}

const VERIFICATION_TOOL = [{
  name: "report_verification",
  description: "Classify the result of a read-only post-action check. Quote exact evidence from the supplied verification finding.",
  input_schema: {
    type: "object",
    properties: {
      status: { type: "string", enum: ["verified", "not_verified", "inconclusive"] },
      summary: { type: "string" },
      evidence: { type: "array", items: { type: "string" } },
    },
    required: ["status", "summary", "evidence"],
  },
}];

export async function verifyRemediation(actionName, params, reason) {
  if (actionName === "locate_led" || actionName === "locate_central_device") {
    return {
      status: "unavailable",
      summary: "The action request was accepted, but read-only telemetry cannot confirm the physical locator LED state.",
      evidence: [],
      toolLog: [],
    };
  }

  const target = JSON.stringify(params);
  let verification;
  try {
    verification = await runJarvisInvestigation(
      `Perform a fresh, READ-ONLY post-action check for the same lab entity and condition. ` +
      `Action attempted: ${actionName}. Target parameters: ${target}. Original reason: ${reason}. ` +
      `Use current platform telemetry to determine whether the action took effect and whether the reported symptom is resolved. ` +
      `Do not make any changes. State what you can and cannot verify.`
    );
  } catch (error) {
    return {
      status: "inconclusive",
      summary: `Post-action read-only verification failed: ${error.message}`,
      evidence: [],
      toolLog: [],
    };
  }
  const sourceEvidence = Array.isArray(verification.observedEvidence)
    ? verification.observedEvidence.join("\n\n") : "";
  const capturedAt = Date.parse(verification.evidenceCapturedAt || "");
  if (!sourceEvidence || !Number.isFinite(capturedAt) || capturedAt > Date.now()
    || Date.now() - capturedAt > REMEDIATION_EVIDENCE_MAX_AGE_MS) {
    return {
      status: "inconclusive",
      summary: sourceEvidence
        ? "The post-action check returned no current direct read-only evidence."
        : "The post-action check returned no direct read-only evidence.",
      evidence: [],
      finding: verification.text,
      toolLog: verification.toolLog,
    };
  }

  const response = await client.messages.create({
    model: JARVIS_MODEL,
    max_tokens: 1024,
    system: cachedSystem(
      "Classify only the supplied post-action read-only finding. Do not infer success from the write response or from the fact that an action was attempted. " +
      "Return verified only when exact evidence shows the intended result, not_verified when exact evidence shows it did not take effect or the issue persists, " +
      "and inconclusive when evidence is absent, stale, conflicting, or insufficient. Quote exact snippets from the direct read-only tool evidence."
    ),
    messages: [{
      role: "user",
      content: `Action: ${actionName}\nReason: ${reason}\n\nPost-action finding:\n${verification.text}` +
        `\n\nDirect read-only tool evidence:\n${sourceEvidence}`,
    }],
    tools: cachedTools(VERIFICATION_TOOL),
    tool_choice: { type: "tool", name: "report_verification" },
  });
  const result = response.content.find(block => block.type === "tool_use" && block.name === "report_verification")?.input;
  const evidence = Array.isArray(result?.evidence) ? result.evidence.filter(
    item => typeof item === "string" && item.trim().length >= 12 && sourceEvidence.includes(item.trim())
  ) : [];
  const validStatus = ["verified", "not_verified", "inconclusive"].includes(result?.status);
  const status = validStatus && result.status !== "inconclusive" && evidence.length === 0
    ? "inconclusive"
    : validStatus ? result.status : "inconclusive";
  return {
    status,
    summary: result?.summary || "No reliable post-action conclusion was available.",
    evidence,
    finding: verification.text,
    toolLog: verification.toolLog,
  };
}
