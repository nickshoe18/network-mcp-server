# HPE Networking MCP Server — Project Context

## Architecture
Docker containers managed via `netops-ui/docker-compose.yml`:
- `hpe-mcp` (port 8000) — main MCP server, ghcr.io/nowireless4u/hpe-networking-mcp:latest
- `netops-backend` (port 3001) — Node.js API backend for NetOps UI
- `netops-frontend` (port 3000) — React web UI via Nginx

## MCP Servers in Claude Code
- `hpe-networking-mcp` — 7 platforms: Mist, Central, GreenLake, ClearPass, Axis, AOS8, UXI
- `juniper-mist-official` — Official Juniper Mist MCP (Marvis Actions, full Mist surface)

## Connected Platforms (hpe-networking-mcp)
| Platform | Tools | Auth | Notes |
|---|---|---|---|
| Juniper Mist | 516 | API Token | Org: Stark Industries, org_id: 5f24e447-1145-4efa-94e0-ccec1a2a00a7, host: api.gc4.mist.com (Google Cloud 4) |
| Aruba Central (New Central) | 655 | OAuth2 (client-credentials) | internal.api.central.arubanetworks.com — includes CNAC (Cloud NAC) + device-collections tools ported from upstream `nowireless4u/hpe-networking-mcp` |
| Classic Central | 5 | OAuth2 (refresh-token) | internal-apigw.central.arubanetworks.com — separate legacy API/product from New Central; needed for devices not yet migrated (e.g. Bat Cave's OfficeSwitch/GarageSwitch, template-managed). Refresh token rotates on every use — see `platforms/classic_central/client.py` |
| HPE GreenLake | 168 | OAuth2 | global.api.greenlake.hpe.com — networking-relevant slice ported from upstream `nowireless4u/hpe-networking-mcp` (device_management, subscription_management, tags, location_management, event, authorization, service_catalog, reporting); first GreenLake platform with write tools (ENABLE_GREENLAKE_WRITE_TOOLS, default false) |
| ClearPass | 84 | OAuth2 | https://10.10.20.5/api (private IP — needs VPN when remote) |
| Aruba Axis | 12 | API Token | admin-api.axissecurity.com |
| AOS8 / Mobility Conductor | 36 | Username/Password | https://10.10.20.7:4343 (ArubaMM-VA, AOS-8 8.13.2.2, self-signed cert — verify_ssl=false), private IP — needs VPN when remote |
| UXI | 11 | OAuth2 | 1 sensor: VNS9LPM0JP (UX-G6EC, Wayne Enterprises group, Rockwall TX) |
| Juniper Security Director Cloud | 4 | Static API key (`x-api-key` header) | api.sdcloud.juniperclouds.net — SD-WAN/SASE site-and-device orchestration (devices, sites); confirmed against the real OpenAPI spec, no firewall security-policy/NAT/address-object API found in that spec. New platform, first pass — read-only |

## Secrets Folder
`~/hpe-networking-mcp/secrets/` — one file per credential, gitignored

## Zscaler SSL Fix
Corporate network intercepts SSL. Fix applied at container startup via volume-mounted entrypoint:
- `docker-entrypoint.sh` — appends Zscaler chain to certifi, patches UXI client dynamically
- `zscaler-full-chain.pem` — 3-cert chain from Mac Keychain
Both volume-mounted into the hpe-mcp container at runtime.

## Key Operational Notes
- **Switch port queries**: Central blocks `show interface 1/1/X` (slash chars rejected)
  - Use: `central_get_switch_vlans(serial_number=SERIAL)` → filter for port
  - Use: `central_get_switch_poe(serial_number=SERIAL)` → filter for port
  - Use: `central_show_commands(serial_number=SERIAL, device_type='cx', commands='show running-config')` → parse interface section
- **Switch serial field**: `serialNumber` not `serial`
- **Central alerts**: require `site_id` — use `central_get_site_name_id_mapping()` first
- **Show commands device_type**: lowercase only — cx, aos-s, aps, gateways
- **Mist tools**: all go via `mist_invoke_tool(name, params)` inside execute
- **Central tools**: all go via `central_invoke_tool(name, params)` inside execute
- **UXI tools**: first-class direct calls — `uxi_list_sensors`, `uxi_get_sensor_status`
- **ClearPass**: offline when remote from 10.10.20.5 (needs local network or VPN)
- **Write tools**: disabled by default. Enable in netops-ui/.env: ENABLE_CENTRAL_WRITE_TOOLS=true. Exception: Classic Central write tools default to **enabled** (ENABLE_CLASSIC_CENTRAL_WRITE_TOOLS=true) per explicit choice when that platform was added

## Claude Desktop Config
`~/Library/Application Support/Claude/claude_desktop_config.json`
- mcp-remote WITHOUT --transport or --sse flags (causes Session not found errors)
- sudo npm install -g mcp-remote@latest if permission errors

## NetOps UI
- URL: http://localhost:3000
- Backend: Node.js at port 3001, connects to hpe-mcp:8000/mcp via local MCP proxy
- System prompt in: `netops-ui/backend/src/routes/chat.js`
- Health endpoint: `netops-ui/backend/src/routes/health.js` (hardcoded ok — MCP /health returns 404)
- Tool limit: 6 meta-tools exposed to UI (execute, search, tags, skills_list, skills_load, get_schema)

## Network Inventory
### Aruba Central
- Sites: Hall of Justice (44056656981), Bat Cave (791595406) — Rockwall County, TX
- OfficeSwitch: CX-6100, serial CN26KNN2Z0, site Bat Cave, IP 10.10.10.4
- Port 1/1/7: trunk, native VLAN 20 (Aruba), tagged VLANs 10,20,30,50,60,200

### Juniper Mist — Stark Industries
- Site: Stark Tower (59f74351-5c94-49bf-adea-dc96f4b132bf), Rockwall TX
- Switch: StarkTowerSW01 (EX3400-48P, MAC 045c6c556ee2) — recurring disconnect events
- AP: c8:78:67:08:56:ea (AP45-US) — currently offline, connected to StarkTowerSW01 ge-0/0/0
- Gateway: StarkWANEdge (SRX300, MAC 0c812665a868)
- Marvis: 11 actions, DFS radar on channels 116/120/124/128 (self-driven), gateway firmware auto-upgraded

## GitHub Repo
https://github.com/nickshoe18/network-mcp-server
- docs/ — Word documents (Tool Reference, macOS guide, Windows guide)
- netops-ui/ — full stack (backend, frontend, nginx, docker-compose)
- docker-entrypoint.sh, zscaler-full-chain.pem — Zscaler fix
- secrets/ and .env gitignored

## Pending Items
- VM hosting on ESXi (Ubuntu 22.04, Docker, clone repo, scp secrets)
- Juniper Apstra credentials (disabled — needs apstra_server, apstra_username, apstra_password)
- Update all three Word docs to reflect latest architecture

Please update CLAUDE.md to add:
- juniper-mist-official MCP server is now connected (Bearer token auth, X-Mist-Base-URL: api.gc4.mist.com)
- Marvis Actions confirmed working - 11 findings in Stark Industries org
- StarkTowerSW01 has recurring disconnect pattern (6 events) - needs investigation
- AP c8:78:67:08:56:ea offline at Stark Tower connected to StarkTowerSW01 ge-0/0/0
- VS Code is now the primary working environment with .mcp.json in repo root
- Mist token needs rotation (was exposed in chat)
- ClearPass reconnected after server rebuild - credentials unchanged
