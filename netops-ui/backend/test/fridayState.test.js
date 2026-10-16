import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { migrateFridayStateFiles } from "../src/fridayState.js";

function withTempDir(run) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "friday-state-"));
  try {
    run(dir);
  } finally {
    fs.rmSync(dir, { recursive: true, force: true });
  }
}

test("legacy poller state is migrated without changing its contents", () => {
  withTempDir(dir => {
    const names = [
      "seen_actions",
      "seen_sle",
      "active_snapshot",
      "pending_resolution",
      "entity_last_alert",
      "seen_central_alerts",
      "central_active_snapshot",
      "central_pending_resolution",
      "findings",
    ];
    for (const name of names) {
      fs.writeFileSync(path.join(dir, `jarvis_${name}.json`), `{"file":"${name}"}`);
    }

    migrateFridayStateFiles(dir);

    for (const name of names) {
      assert.equal(fs.existsSync(path.join(dir, `jarvis_${name}.json`)), false);
      assert.equal(fs.readFileSync(path.join(dir, `friday_${name}.json`), "utf8"), `{"file":"${name}"}`);
    }
  });
});

test("state migration does not overwrite or partially migrate on conflicts", () => {
  withTempDir(dir => {
    const legacy = path.join(dir, "jarvis_seen_actions.json");
    const current = path.join(dir, "friday_seen_actions.json");
    const pendingLegacy = path.join(dir, "jarvis_active_snapshot.json");
    const pendingCurrent = path.join(dir, "friday_active_snapshot.json");
    fs.writeFileSync(legacy, "legacy");
    fs.writeFileSync(current, "current");
    fs.writeFileSync(pendingLegacy, "unmigrated");

    assert.throws(() => migrateFridayStateFiles(dir), /Resolve each pair without discarding state/);
    assert.equal(fs.readFileSync(legacy, "utf8"), "legacy");
    assert.equal(fs.readFileSync(current, "utf8"), "current");
    assert.equal(fs.existsSync(pendingLegacy), true);
    assert.equal(fs.existsSync(pendingCurrent), false);
  });
});
