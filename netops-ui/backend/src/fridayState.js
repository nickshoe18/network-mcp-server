import fs from "node:fs";
import path from "node:path";

const STATE_FILES = [
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

export function migrateFridayStateFiles(dataDir) {
  fs.mkdirSync(dataDir, { recursive: true });
  const migrations = STATE_FILES.map(name => ({
    oldPath: path.join(dataDir, `jarvis_${name}.json`),
    newPath: path.join(dataDir, `friday_${name}.json`),
  }));

  const conflicts = migrations
    .filter(({ oldPath, newPath }) => fs.existsSync(oldPath) && fs.existsSync(newPath))
    .map(({ oldPath, newPath }) => `${path.basename(oldPath)} and ${path.basename(newPath)}`);
  if (conflicts.length) {
    throw new Error(`FRIDAY state migration found both legacy and new files: ${conflicts.join("; ")}. Resolve each pair without discarding state, then restart.`);
  }

  for (const { oldPath, newPath } of migrations) {
    if (!fs.existsSync(oldPath)) continue;
    fs.linkSync(oldPath, newPath);
    fs.unlinkSync(oldPath);
    console.warn(`[poller] migrated persisted state ${path.basename(oldPath)} to ${path.basename(newPath)}`);
  }
}
