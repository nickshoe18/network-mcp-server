---
name: client-cannot-connect
title: Client cannot connect, get an IP, or reach the network
description: |
  First-line triage for a wireless or wired client that will not associate, gets no IP or a 169.254 address,
  or has an address but no connectivity. Use when the report is "device X can't join SSID Y", "no IP",
  "connected but no internet", or "captive portal never appears".
platforms: [mist, central, uxi]
tags: [client, wireless, wired, dhcp, triage, l1]
tools: [mist_search_site_wireless_client_events, mist_search_site_wired_clients, mist_list_org_wlans, mist_troubleshoot_org, mist_search_site_sw_or_gw_ports, uxi_get_sensor_status]
---

# Client cannot connect, get an IP, or reach the network

## Objective

Find the last stage the client completed (associate -> auth -> DHCP -> gateway ARP -> DNS -> traffic), then
hand off to the right check. The failing stage is the diagnosis.

## Prerequisites

- Client identifier (MAC, IP, hostname, or "the UXI sensor"), the SSID or port, the site, and roughly when.
- Whether this device works on another SSID or port (if yes, the client is not the problem).
- Lab defaults: Mist org and site IDs are in the project CLAUDE.md. The Stark Tower site holds the switch, AP and SRX.

## Procedure

### Step 1 - Pull the client's recent events

**Tool:** `mist_search_site_wireless_client_events(site_id, duration="30m", ssid="<SSID>")`
**Why:** The event sequence shows exactly where it stops. This tool does NOT accept a `mac` filter - filter the
returned list by `mac` yourself. Results cap at 100, so a noisy SSID can hide your client; narrow `duration`.
**Wired client:** `mist_search_site_wired_clients(site_id, port_id="ge-0/0/N")` - `ip` empty with a MAC learned
means link and VLAN are fine but no DHCP.

### Step 2 - Read the sequence

| Last event seen | Meaning | Go to |
|---|---|---|
| Nothing for this MAC | Never associated: out of range, SSID band not supported (check WLAN `bands`), wrong SSID, client not yet retrying | Step 3 |
| `MARVIS_EVENT_CLIENT_AUTH_FAILURE` (reason 14/15) | PSK mismatch or 4-way handshake timeout | Check key / encryption type |
| `CLIENT_DEAUTHENTICATED "throttled N times"` | Client is reconnecting too fast; often randomized MAC churn or an encryption mismatch | Step 3, Step 4 |
| `CLIENT_AUTH_ASSOCIATION (vlan: N)` then `MARVIS_EVENT_CLIENT_DHCP_FAILURE` | Associated, no DHCP answer on VLAN N | Run the `dhcp-troubleshooting` runbook |
| `CLIENT_IP_ASSIGNED` but no `CLIENT_GW_ARP_OK` | Has an IP, gateway unreachable: VLAN or gateway interface | Verify the gateway IP exists (SRX `show interfaces irb terse`) |
| `CLIENT_GW_ARP_OK` but no `CLIENT_DNS_OK` | Gateway fine, DNS failing: check the DHCP scope's DNS servers | dhcp-troubleshooting step 1 |
| All OK, then `..._CAPTIVE_PORT_FLOW_REDIRECT` | Working; web traffic is being sent to the portal | Portal is enabled by design |
| `SA_QUERY_TIMEOUT` (reason 9) after a working session | Client dropped and rejoined; UXI sensors do this each test cycle | Benign |

### Step 3 - Confirm the WLAN's VLAN and encryption

**Tool:** `mist_list_org_wlans(org_id)` (site WLAN lists can be empty when WLANs are org-scoped)
**Why:** Compare `vlan_id`, `bands`, `auth` (open/OWE/PSK) with what the client is doing. An event's `vlan` field
is authoritative for where the client actually landed.

### Step 4 - Isolate the client

- Does the same device work on a different SSID? Then it is SSID- or VLAN-specific, not the client.
- Randomized MAC: events carry `random_mac: true`. macOS/iOS/Android set Private Address per network.
- For wireless-only failures, test a wired client on the same VLAN if you can (needs an authorized port override).

### Step 5 - Marvis view (supporting evidence only)

**Tool:** `mist_troubleshoot_org(org_id, site_id, mac="<mac without colons>", type="client")`
Recommendations here are generic. Never present them as root cause.

## Output formatting

Use the Jarvis ticket format. Put the failing stage and the timestamped events in Findings.

## Example

> "My phone can't get an IP on the Guest SSID."
