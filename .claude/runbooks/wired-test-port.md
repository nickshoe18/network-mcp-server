---
name: wired-test-port
title: Wired test port on a chosen VLAN (isolate wireless from network)
description: |
  Temporarily put one unused switch port on a VLAN so a wired device can test DHCP and connectivity, removing the
  AP and WLAN from the picture, then remove it. This makes a CONFIG CHANGE to the switch, so it needs explicit
  authorization from the caller for that port and VLAN. Use to isolate "wireless only" problems.
platforms: [mist]
tags: [test, isolation, switch, port, vlan, l1]
tools: [mist_get_site_device, mist_update_site_local_switch_port_config, mist_delete_site_local_switch_port_config, mist_search_site_sw_or_gw_ports, mist_search_site_wired_clients, mist_search_site_device_events, mist_start_site_locate_device, mist_stop_site_locate_device]
---

# Wired test port

## Objective

Give a wired device a known-good path into one VLAN so you can tell whether DHCP and the network work without
the AP or WLAN involved.

## Prerequisites

- The caller has authorized this exact port and VLAN and knows a switch change is involved.
- A port not used by anything: check the switch template's `switch_matching` rules and current stats, and pick a
  port with no `port_usage` and no clients.

## Procedure

### Step 1 - Read existing overrides FIRST

`mist_get_site_device(site_id, device_id)` and read `local_port_config`. The update call REPLACES all local port
overrides, so the body must include every existing entry plus the new one. Record what was there.

### Step 2 - Apply

`mist_update_site_local_switch_port_config(site_id, device_id, body={"ge-0/0/N": {"mode": "access",
"port_network": "<network name>", "disabled": false}, ...existing...})`. Needs `confirmed: true` only with the
caller's authorization.

### Step 3 - Confirm it took

Wait for `SW_CONFIGURED` in `mist_search_site_device_events`. Then `mist_search_site_sw_or_gw_ports(site_id, mac,
port_id)`: `vlan_ids` must show the VLAN and `up: true` once the device is plugged in. An early read can show the
old VLAN; re-read.

### Step 4 - Identify the port for the operator

`mist_start_site_locate_device` blinks EVERY port LED on the switch for about 5 minutes; it cannot flash one port.
Tell the operator that, give the port number, and stop it with `mist_stop_site_locate_device` when done.

### Step 5 - Test

`mist_search_site_wired_clients(site_id, port_id=...)`: MAC learned with a VLAN and an `ip`. Empty `ip` with a
learned MAC means link and VLAN are fine but no DHCP (run `dhcp-troubleshooting`). On the SRX: `show dhcp server
binding` for the lease.

### Step 6 - Remove it

Restore the recorded overrides. If NO other overrides existed, `mist_delete_site_local_switch_port_config` clears
them, but it deletes ALL local overrides, so use it only after Step 1 showed the test port was the only one.
Confirm with the port stats afterwards, and tell the caller the port is back to its original usage.

## Output formatting

Report: port and VLAN used, what was there before, the result of the test, and confirmation of removal. If you
could not remove it, say so prominently.

## Example

> "Set up a wired test port on the Guest VLAN."
