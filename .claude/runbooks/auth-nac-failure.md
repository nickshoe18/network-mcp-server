---
name: auth-nac-failure
title: 802.1X, MAC-auth, or NAC authentication failure
description: |
  Triage a client or port that fails authentication or lands on the wrong VLAN/role: Mist NAC, switch dot1x
  ports, and ClearPass. Use for "can't authenticate", "wrong VLAN after login", "rejected", "RADIUS timeout".
  Less exercised than the Wi-Fi/DHCP runbooks: treat conclusions as medium confidence unless corroborated.
platforms: [mist, clearpass]
tags: [nac, 802.1x, radius, clearpass, auth, l1]
tools: [mist_search_site_nac_client_events, mist_list_org_wlans, mist_search_site_wireless_client_events, clearpass_get_sessions, clearpass_get_system_events, clearpass_get_auth_source_status]
---

# Authentication or NAC failure

## Objective

Tell "never reached the auth server", "rejected by the auth server", and "accepted but placed wrongly" apart.

## Prerequisites

- Client MAC or username, the SSID or switch port, and roughly when.
- ClearPass is on a private IP and only reachable from the lab LAN or VPN. If `health` says it is unavailable,
  say so and continue with the Mist side only.

## Procedure

### Step 1 - What does the network expect?

WLAN: `mist_list_org_wlans` - `auth.type` (psk/eap/open/OWE), `mist_nac.enabled`, dynamic VLAN.
Switch port: the port usage in the switch template (for example `dot1x`, `port_auth`, `mac_auth`).

### Step 2 - Client-side events

`mist_search_site_wireless_client_events(site_id, duration="30m", ssid=...)` (filter by `mac` yourself).
- Auth failure with a PSK reason means wrong key; EAP timeouts point at the RADIUS path.
- Association fine but no traffic and portal redirects: a captive portal, not NAC.

### Step 3 - Mist NAC events

`mist_search_site_nac_client_events(site_id, ...)` - look for the rule matched, auth type, VLAN assigned, and
rejection reason. No events at all for the client means the request never reached Mist NAC.

### Step 4 - ClearPass (if reachable)

`clearpass_get_sessions` for the endpoint; `clearpass_get_system_events` for RADIUS errors;
`clearpass_get_auth_source_status` if the auth source (AD/LDAP) may be down. Compare the role and VLAN returned
with what the enforcement policy should return.

### Step 5 - RADIUS reachability

`mist_start_site_switch_radius_synthetic_test` exists but returns output only over a websocket, so it cannot be
read here. Infer reachability from whether requests appear in ClearPass or Mist NAC.

## Decision matrix

| Finding | Likely cause | Action |
|---|---|---|
| No request seen at the auth server | Path/NAS config/shared secret | Escalate with the NAS and server addresses |
| Reject with a policy reason | Credentials, cert, or policy | Report the reason string verbatim |
| Accept but wrong VLAN/role | Role mapping or enforcement policy | Escalate the policy name |
| Auth source down | AD/LDAP outage | Escalate to the directory owner |

## Output formatting

Jarvis ticket format; quote the exact rejection or event text.

## Example

> "My laptop keeps failing 802.1X on the wired port."
