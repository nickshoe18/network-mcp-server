# Handoff

Last updated: 2026-10-15, after commit `86158a4`.

## What this repo actually contains

Two architecturally separate things that happen to live together:

1. **`hpe-networking-mcp` (the MCP server)** — exposes ~4,000+ tools across Juniper Mist, Aruba
   Central (New + Classic), ClearPass, AOS8/Mobility Conductor, UXI, GreenLake, Axis, Juniper
   Security Director Cloud, and SRX (NETCONF). It's a standard MCP (Model Context Protocol)
   server — client-agnostic. Anything that speaks MCP can connect to it (Claude Code today;
   GitHub Copilot's VS Code agent mode could too, since MCP is an open protocol, not an
   Anthropic-only thing).
2. **Jarvis** — a Claude-specific system built *on top of* that MCP server. Two parts:
   - An interactive Claude Code subagent (`.claude/agents/jarvis.md`) — Level 1 network engineer
     triage, read-only by default, a few explicitly-authorizable write actions.
   - An autonomous "autopilot" backend (`netops-ui/backend/`) that polls Mist's Marvis Actions,
     Mist SLE, and Aruba Central alerts; runs real investigations; proposes narrow
     human-approved remediation.

**Important distinction if anyone considers moving this to a different AI tool:** the MCP server
is portable (point any MCP client at `http://localhost:8000/mcp`). Jarvis is not — the autopilot
calls Anthropic's Messages API directly (`@anthropic-ai/sdk`, Claude-specific prompt caching,
Claude's tool-use format) and the subagent format is Claude-Code-specific. There's no equivalent
"swap the backend" path to GitHub Copilot or another vendor without a real rewrite — Copilot
doesn't expose a general server-callable API the way Anthropic's does.

## Running the stack

Everything lives under `netops-ui/docker-compose.yml`. From `netops-ui/`:

```
docker compose up -d --build        # bring everything up, rebuild changed images
docker compose ps                   # check container health
docker logs netops-backend -f       # watch Jarvis's poller + chat traffic
```

Key services: `hpe-mcp` (main lab server, :8000), `hpe-mcp-autopilot` (isolated write-capable
instance Stage 2 remediation actually executes through, :8005), `hpe-mcp-bobcats/jackets/
leopards/panthers/knights` (per-customer isolated tenants, :8001-8006), `backend` (:3001, runs
`poller.js`), `frontend` (:3000, the NetOps UI).

Separately, **not** in docker-compose: a standalone Panthers channel-utilization dashboard at
`reports-panthers/channel_monitor/`, started manually (`poller.py` + `python3 -m http.server
8099 --bind 127.0.0.1`), served at `http://127.0.0.1:8099`. Localhost-only by design.

## What changed most recently (commit `86158a4`)

- **Alerting reliability**: fixed a near-continuous duplicate-email bug. SLE breach dedup moved
  to a per-metric episode model (the old "hourly bucket" id was drifting every ~2 minutes, not
  staying fixed for an hour). Marvis action resolution now requires 2 consecutive polls of
  absence before declaring resolved (a single poll's absence was flickering and firing repeat
  "resolved" emails for the same still-open issue). Added a per-entity flap cooldown and an
  in-flight poll-overlap guard.
- **Prompt caching**: every Claude call Jarvis makes was fully uncached before this — a 15-turn
  investigation re-billed its entire growing conversation every turn. `anthropicCache.js` now
  caches the system prompt, tool definitions, and growing message history.
- **New Stage 2 action**: `release_dhcp_lease` (Mist only — `mist_release_site_device_dhcp_lease`,
  `macs` + `network`, scoped to the DHCP-serving gateway device).
- **Aruba Central autopilot support**: Central alerts are now a second trigger source alongside
  Marvis/SLE, with 3 new Stage 2 actions (`reboot_central_device`, `disconnect_central_client`,
  `locate_central_device`). No Central equivalent of DHCP lease release exists.

See `git log` and the commit message on `86158a4` for the full detail.

## Known limitations / open items

- Mist's org inventory claim via API (`mist_create_org_async_claim`) returns `invalid code` even
  immediately after a release-and-rescan; root cause unresolved. The Mist app itself claims fine
  — a Mist support ticket is the recommended next step if this needs solving via API.
- `StarkTowerSW01`'s recurring disconnect pattern (6+ events) has never been root-caused.
- Server/DHCP-reachability monitoring for Jarvis was explicitly deferred by the user until
  Stage 0–2 were fully running and tested — they now are, so this is a reasonable next pickup.
- Batch device claim/assignment (vs. one-at-a-time) was explicitly deferred to "the future."
- The standalone Panthers dashboard's external-access scoping (who/what network reach beyond
  localhost) was raised once and never resumed — don't assume it's intentionally localhost-only
  forever, just that nobody's decided otherwise yet.

## Conventions worth knowing before touching anything

- **Secrets**: one file per credential under `secrets/` (lab) or `secrets-<codename>/` (customer
  tenants), gitignored. Never paste secrets into chat — write via
  `printf '%s' 'VALUE' > file && chmod 600 file`.
- **Customer tenants**: real customer names never appear in code, local container names, or
  commits — only internal codenames (Bobcats, Jackets, Leopards, Panthers, Knights). Each is a
  fully isolated Docker container + secrets directory.
- **Write tools default OFF** per platform (`ENABLE_<PLATFORM>_WRITE_TOOLS`), flipped on
  deliberately per environment. The one standing exception: Classic Central defaults write-on.
- **Destructive actions** (delete, bulk claim, etc.) go through `confirm_gated_invoke` — the
  MCP server's own structural confirmation gate — independent of whatever the calling agent's
  own prompt says. Stage 2's remediation path is additionally isolated to its own container with
  its own narrow write-tool allowlist, and `confirmed: true` is only ever set by fixed backend
  code, never model-generated text.
- Full architecture detail, inventory, and per-platform notes live in `CLAUDE.md` at the repo
  root — this file is meant to complement it, not replace it.
