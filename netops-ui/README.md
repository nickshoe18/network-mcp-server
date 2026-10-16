# HPE NetOps UI

Web-based chat interface for the HPE Networking MCP Server.
Connects Claude to Mist, Central, GreenLake, ClearPass, Axis, and UXI via a browser.

## Quick Start

```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY and SECRETS_DIR
docker compose up --build
```

Open http://localhost:3000

## FRIDAY settings

Configure the assistant and autopilot with `FRIDAY_*` environment variables in `.env`:
`FRIDAY_MODEL`, `FRIDAY_AUTOPILOT_ENABLED`, `FRIDAY_POLL_INTERVAL_MS`,
`FRIDAY_DATA_DIR`, `FRIDAY_SLE_EPISODE_GAP_MS`,
`FRIDAY_SLE_RENOTIFY_COOLDOWN_MS`, `FRIDAY_RESOLUTION_CONFIRM_POLLS`,
`FRIDAY_ENTITY_ALERT_COOLDOWN_MS`, and `FRIDAY_REMEDIATION_ENABLED`.
The defaults are unchanged; remediation remains disabled unless explicitly enabled.

The corresponding `JARVIS_*` variables remain accepted for this transition release only.
If both names are set, `FRIDAY_*` takes precedence. Use of a legacy key emits a startup
warning; update `.env` to the `FRIDAY_*` name before the next release.
The old chat API mode value `jarvis` is likewise accepted with a deprecation warning for
this transition release; the frontend now uses `friday` and migrates the saved mode.
