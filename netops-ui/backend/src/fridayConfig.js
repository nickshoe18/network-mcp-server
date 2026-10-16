const SETTINGS = new Set([
  "MODEL",
  "AUTOPILOT_ENABLED",
  "POLL_INTERVAL_MS",
  "DATA_DIR",
  "SLE_EPISODE_GAP_MS",
  "SLE_RENOTIFY_COOLDOWN_MS",
  "RESOLUTION_CONFIRM_POLLS",
  "ENTITY_ALERT_COOLDOWN_MS",
  "REMEDIATION_ENABLED",
]);

const warnedAliases = new Set();

export function fridaySetting(name, fallback) {
  if (!SETTINGS.has(name)) throw new Error(`Unsupported FRIDAY setting: ${name}`);

  const fridayKey = `FRIDAY_${name}`;
  const fridayValue = process.env[fridayKey];
  if (fridayValue !== undefined && fridayValue !== "") return fridayValue;

  const legacyKey = `JARVIS_${name}`;
  const legacyValue = process.env[legacyKey];
  if (legacyValue !== undefined && legacyValue !== "") {
    if (!warnedAliases.has(legacyKey)) {
      console.warn(`[config] ${legacyKey} is deprecated; use ${fridayKey}. Legacy aliases are supported for this transition release only.`);
      warnedAliases.add(legacyKey);
    }
    return legacyValue;
  }

  return fallback;
}
