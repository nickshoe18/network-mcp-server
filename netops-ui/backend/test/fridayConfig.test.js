import test from "node:test";
import assert from "node:assert/strict";
import { fridaySetting } from "../src/fridayConfig.js";

test("FRIDAY settings take precedence and defaults are preserved", () => {
  const oldFriday = process.env.FRIDAY_MODEL;
  const oldJarvis = process.env.JARVIS_MODEL;
  const oldAutopilot = process.env.FRIDAY_AUTOPILOT_ENABLED;
  const oldLegacyAutopilot = process.env.JARVIS_AUTOPILOT_ENABLED;
  const oldRemediation = process.env.FRIDAY_REMEDIATION_ENABLED;
  const oldLegacyRemediation = process.env.JARVIS_REMEDIATION_ENABLED;
  try {
    process.env.FRIDAY_MODEL = "friday-model";
    process.env.JARVIS_MODEL = "legacy-model";
    assert.equal(fridaySetting("MODEL", "default-model"), "friday-model");

    delete process.env.FRIDAY_MODEL;
    delete process.env.JARVIS_MODEL;
    assert.equal(fridaySetting("MODEL", "default-model"), "default-model");
    delete process.env.FRIDAY_AUTOPILOT_ENABLED;
    delete process.env.JARVIS_AUTOPILOT_ENABLED;
    delete process.env.FRIDAY_REMEDIATION_ENABLED;
    delete process.env.JARVIS_REMEDIATION_ENABLED;
    assert.equal(fridaySetting("AUTOPILOT_ENABLED", "true"), "true");
    assert.equal(fridaySetting("REMEDIATION_ENABLED", "false"), "false");
  } finally {
    if (oldFriday === undefined) delete process.env.FRIDAY_MODEL;
    else process.env.FRIDAY_MODEL = oldFriday;
    if (oldJarvis === undefined) delete process.env.JARVIS_MODEL;
    else process.env.JARVIS_MODEL = oldJarvis;
    if (oldAutopilot === undefined) delete process.env.FRIDAY_AUTOPILOT_ENABLED;
    else process.env.FRIDAY_AUTOPILOT_ENABLED = oldAutopilot;
    if (oldLegacyAutopilot === undefined) delete process.env.JARVIS_AUTOPILOT_ENABLED;
    else process.env.JARVIS_AUTOPILOT_ENABLED = oldLegacyAutopilot;
    if (oldRemediation === undefined) delete process.env.FRIDAY_REMEDIATION_ENABLED;
    else process.env.FRIDAY_REMEDIATION_ENABLED = oldRemediation;
    if (oldLegacyRemediation === undefined) delete process.env.JARVIS_REMEDIATION_ENABLED;
    else process.env.JARVIS_REMEDIATION_ENABLED = oldLegacyRemediation;
  }
});

test("legacy settings are honored and warned about once", () => {
  const oldFriday = process.env.FRIDAY_POLL_INTERVAL_MS;
  const oldJarvis = process.env.JARVIS_POLL_INTERVAL_MS;
  const originalWarn = console.warn;
  const warnings = [];
  try {
    delete process.env.FRIDAY_POLL_INTERVAL_MS;
    process.env.JARVIS_POLL_INTERVAL_MS = "90000";
    console.warn = message => warnings.push(message);

    assert.equal(fridaySetting("POLL_INTERVAL_MS", 120000), "90000");
    assert.equal(fridaySetting("POLL_INTERVAL_MS", 120000), "90000");
    assert.equal(warnings.length, 1);
    assert.match(warnings[0], /JARVIS_POLL_INTERVAL_MS.*FRIDAY_POLL_INTERVAL_MS/);
  } finally {
    console.warn = originalWarn;
    if (oldFriday === undefined) delete process.env.FRIDAY_POLL_INTERVAL_MS;
    else process.env.FRIDAY_POLL_INTERVAL_MS = oldFriday;
    if (oldJarvis === undefined) delete process.env.JARVIS_POLL_INTERVAL_MS;
    else process.env.JARVIS_POLL_INTERVAL_MS = oldJarvis;
  }
});

test("unsupported settings are rejected", () => {
  assert.throws(() => fridaySetting("UNEXPECTED", "fallback"), /Unsupported FRIDAY setting/);
});
