---
name: port-or-ap-down
title: Switch port, AP, or device is down or flapping
description: |
  First-line triage when a device shows offline, a switch port has no link, or something is flapping.
  Use for "AP is offline", "nothing on port X", "device disconnected", "link keeps bouncing".
platforms: [mist, central]
tags: [port, ap, switch, link, down, flapping, l1]
tools: [mist_search_org_inventory, mist_list_org_devices_stats, mist_search_site_sw_or_gw_ports, mist_search_site_device_events, mist_search_site_wired_clients, mist_start_site_locate_device, mist_stop_site_locate_device, central_get_devices, central_get_alerts]
---

# Switch port, AP, or device is down or flapping

## Objective

Decide whether the fault is the device, the port, the cable, or something upstream, and give the operator a
precise next action.

## Prerequisites

- Device name or MAC, or the switch and port number, and the site.
- Note: the lab AP normally sits on the lab switch port `ge-0/0/0` (dynamic AP port assignment).

## Procedure

### Step 1 - Device state

**Tools:** `mist_search_org_inventory(org_id, site_id, type="ap|switch|gateway")` (the filter is `type`, not
`device_type`), `mist_list_org_devices_stats(org_id, type=..., mac=<no colons>)`.
**Read:** `status`, `last_seen`, `uptime`. A short uptime means it rebooted recently. For a gateway, also read
`module_stat[].status`: it can differ from the top-level status.
**Aruba Central devices:** `central_get_devices`; for alerts call `central_get_site_name_id_mapping` first, then
`central_get_alerts(site_id=...)` (it requires a `site_id`).

### Step 2 - Port state

**Tool:** `mist_search_site_sw_or_gw_ports(site_id, mac=<switch mac>, port_id="ge-0/0/N")`
**Read:** `up`, `speed`, `full_duplex`, `rx_errors`/`tx_errors`, `last_flapped`, `port_mode`, `vlan_ids`,
`mac_count`, `stp_state`, `poe_on`.
- `up: false` right after someone plugged in: re-read after a minute, stats lag.
- Speed 100 or half duplex on a gigabit port suggests a bad cable or a forced setting.
- `vlan_ids` differing from what the port profile says means a config push has not landed yet.

### Step 3 - Event history

**Tool:** `mist_search_site_device_events(site_id, mac=<no colons>, duration="1h")`
**Read:** `SW_PORT_UP` / `SW_PORT_DOWN` with `ifName`, `SW_DYNAMIC_PORT_ASSIGNED`, `SW_CONFIGURED` /
`SW_CONFIG_CHANGED_BY_USER`. A down/up pair seconds apart is a flap; many pairs is a cabling or PoE problem.

### Step 4 - What is at the other end?

**Tool:** `mist_search_site_wired_clients(site_id, port_id=...)` - `source: lldp` entries identify the neighbor.
For an AP, check that its port carries the management VLAN and that PoE is on and not constrained.

### Step 5 - Upstream

Check the uplink port (`ge-0/0/46-47` on the lab switch) and the gateway's status. A device that is offline
because its uplink or the gateway is down is not itself faulty.

## Cable test (only when the caller asks for a test)

For a flapping or errored copper port, run a TDR from the switch:
`uv run --with websockets python .claude/tools/mist_device_cmd.py cable_test --device switch --port ge-0/0/N`.
Pair lengths and open/short results point at a cable fault. It can briefly disturb the link, so say so first, and
never run it on the uplink port (`ge-0/0/46-47`).

## Safe actions (only if the caller authorizes them)

- Start locate to identify hardware: `mist_start_site_locate_device` blinks EVERY port LED on a switch. Always
  follow with `mist_stop_site_locate_device`.
- Reboot one AP: `mist_restart_site_device`. Expect a short outage; state that.

## Decision matrix

| Finding | Likely cause | Action |
|---|---|---|
| Port `up: false`, no LLDP, no MAC | Cable, wrong port, or dead endpoint | Ask the operator to reseat/try another port; use locate |
| Port up, device offline | Device boot/IP/VLAN, or upstream | Check management VLAN and gateway |
| Repeated up/down events | Bad cable, PoE budget, failing NIC | Escalate with the event timestamps |
| Everything on the switch offline | Switch or uplink | Check uplink and gateway first |
| Config change queued, not committed | Push pending | Wait for `SW_CONFIGURED`; SRX takes about 4 min |

## Output formatting

Jarvis ticket format with the port/device values and timestamps in Findings.

## Example

> "The AP in the lab keeps dropping."
