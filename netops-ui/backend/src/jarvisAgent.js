import Anthropic from "@anthropic-ai/sdk";
import { JARVIS_SYSTEM, JARVIS_TOOLS, JARVIS_MODEL, readRunbook, checkReadOnly } from "./jarvis.js";
import { initSession, mcpCall } from "./routes/chat.js";
import { rebootAp, disconnectClient, setLocateLed, remediationEnabled } from "./remediation.js";

const client = new Anthropic({ apiKey: process.env.ANTHROPIC_API_KEY });
const MAX_TURNS = 15;

// Runs one self-contained, read-only Jarvis investigation to completion and returns
// the final answer text plus a log of what it looked at. Used by the autopilot
// poller (poller.js) — no streaming, no user in the loop, same read-only gate
// (checkReadOnly) as the interactive Jarvis chat mode uses.
export async function runJarvisInvestigation(promptText) {
  const sessionId = await initSession();
  let messages = [{ role: "user", content: promptText }];
  const toolLog = [];

  for (let turn = 0; turn < MAX_TURNS; turn++) {
    const response = await client.messages.create({
      model: JARVIS_MODEL,
      max_tokens: 8192,
      system: JARVIS_SYSTEM,
      messages,
      tools: JARVIS_TOOLS,
    });

    if (response.stop_reason !== "tool_use") {
      const text = response.content.filter(b => b.type === "text").map(b => b.text).join("\n").trim();
      return { text, toolLog };
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
        }
        toolResults.push({ type: "tool_result", tool_use_id: toolUse.id, content: [{ type: "text", text: resultText }] });
      } catch (e) {
        toolResults.push({ type: "tool_result", tool_use_id: toolUse.id, content: [{ type: "text", text: "Error: " + e.message }], is_error: true });
      }
    }

    messages = [...messages, { role: "assistant", content: response.content }, { role: "user", content: toolResults }];
  }

  return { text: "(investigation did not conclude within the turn limit — see tool log)", toolLog };
}

// ── Stage 2: remediation proposal (propose only — never executes) ──────────────
// A separate, single-turn, narrowly-scoped call from the read-only investigation above.
// This function ONLY decides and returns a proposal; it has no access to remediation.js's
// execute functions at all, so there is no code path from here to the network. A human
// must separately approve a stored proposal (routes/findings.js POST /:id/approve) before
// anything runs — see remediation.js for the actual write path and its own gates.

const REMEDIATION_PROPOSAL_TOOLS = [
  {
    name: "reboot_ap",
    description: "Reboot one AP that is online but wedged/misbehaving (bad radio/software state). Do NOT propose this for an AP with no connectivity at all — a cloud-issued reboot command cannot reach a fully disconnected device.",
    input_schema: {
      type: "object",
      properties: {
        site_id: { type: "string" }, device_id: { type: "string", description: "Mist device id, format 00000000-0000-0000-1000-<mac>" },
        reason: { type: "string", description: "One sentence: why this would be safe and is warranted" },
      },
      required: ["site_id", "device_id", "reason"],
    },
  },
  {
    name: "disconnect_client",
    description: "Disconnect one specific misbehaving wireless client. It will likely reconnect on its own — this is a nudge, not a ban.",
    input_schema: {
      type: "object",
      properties: { site_id: { type: "string" }, client_mac: { type: "string" }, reason: { type: "string" } },
      required: ["site_id", "client_mac", "reason"],
    },
  },
  {
    name: "locate_led",
    description: "Start or stop blinking one device's LED for physical identification. Purely cosmetic — never fixes anything, only aids an on-site human.",
    input_schema: {
      type: "object",
      properties: { site_id: { type: "string" }, device_id: { type: "string" }, enabled: { type: "boolean" }, reason: { type: "string" } },
      required: ["site_id", "device_id", "enabled", "reason"],
    },
  },
  {
    name: "no_action",
    description: "None of the above is clearly a good idea for this specific issue, OR the target entity isn't confidently and exactly identified from the investigation. Use this whenever in doubt.",
    input_schema: { type: "object", properties: { reason: { type: "string" } }, required: ["reason"] },
  },
];

const REMEDIATION_PROPOSAL_SYSTEM = JARVIS_SYSTEM + `

You are now proposing a possible next action, not investigating and not executing anything — you have no ability to act, only to suggest. A read-only investigation has already run; its full finding is below. Decide whether exactly one of your 3 real actions would be a reasonable thing to suggest to a human, using ONLY ids/MACs that literally appear in the investigation text — never infer or guess an id. If there is any doubt, the entity isn't uniquely identified, the issue doesn't match one of the 3 real actions, or the investigation itself was inconclusive, call no_action and say why. You must call exactly one tool. A human will read your suggestion and decide separately whether to approve it — nothing happens automatically.`;

export async function proposeRemediation(investigationText, triggerSummary) {
  const response = await client.messages.create({
    model: JARVIS_MODEL,
    max_tokens: 1024,
    system: REMEDIATION_PROPOSAL_SYSTEM,
    messages: [{ role: "user", content: `Trigger: ${triggerSummary}\n\nInvestigation finding:\n\n${investigationText}` }],
    tools: REMEDIATION_PROPOSAL_TOOLS,
    tool_choice: { type: "any" },
  });

  const toolUse = response.content.find(b => b.type === "tool_use");
  if (!toolUse || toolUse.name === "no_action") {
    return { proposal: "no_action", reason: toolUse?.input?.reason || "model did not call a tool (unexpected)" };
  }
  return { proposal: toolUse.name, params: toolUse.input, reason: toolUse.input.reason };
}
