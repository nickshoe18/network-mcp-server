---
name: network-status-update
title: Network status update
description: |
  Produce a short, scannable status update for the whole lab network: platform reachability, devices offline,
  open alarms, recent configuration activity and pending changes, and UXI sensor state. Use when asked for
  "status", "update", "how's the network", or a periodic check-in. Written to be read on a phone.
platforms: [mist, central, clearpass, aos8, uxi, greenlake, axis]
tags: [status, health, update, monitoring, l1]
tools: [health, mist_search_org_alarms, mist_list_org_devices_stats, mist_search_site_device_events, central_get_alerts, uxi_get_sensor_status]
---

# Network status update

## Objective

Answer "is everything OK, and has anything changed?" in under 15 lines, with red/amber/green per area and a
clear "needs attention" list. Read-only.

## Procedure

### Step 1 - Platform reachability

**Tool:** `health()` (all platforms). `unavailable` for ClearPass and AOS8 is expected when off the lab LAN or VPN.
Report reachability as reported; do not investigate unless the caller asks.

### Step 2 - Devices

**Tool:** `mist_list_org_devices_stats(org_id, type="switch|ap|gateway")` for each type.
Count `status != connected`. Note any device with `uptime` under an hour (recent reboot). For the gateway also
check `module_stat[].status`.
**Central:** `central_get_site_name_id_mapping` (sorted worst health first, with alert counts), then
`central_get_alerts(site_id=...)` for any site with alerts. It requires a `site_id`.

### Step 3 - Alarms

**Tool:** `mist_search_org_alarms(org_id, duration="1d")`. Group by type and severity; list only critical and
warn, newest first. Marvis suggestions are informational.

**Marvis:** follow the `marvis-review` runbook for active Marvis Actions and add its one-line summary here. If
the Marvis source is unavailable, say "Marvis: not checked" rather than omitting it.

### Step 4 - Configuration activity and pending changes

**Tool:** `mist_search_site_device_events(site_id, mac=<gateway mac>, duration="24h")` and the same for the switch.
- `GW_CONFIGURED` / `SW_CONFIGURED` = committed. Summarize what the `config_diff` changed in one line.
- A `*_CONFIG_CHANGED_BY_USER` with no later `*_CONFIGURED` for more than 10 minutes = a stuck or pending push:
  flag it.
- `GW_NON_MIST_USER_LOGIN` = someone logged in directly to the SRX CLI; mention it.
- Ignore commits whose diff is only NTP server rotation; they are routine.

### Step 5 - UXI

**Tool:** `uxi_get_sensor_status(sensor_id)` for the lab sensor. `isOnline`, `isTesting`, and the issues list
(codes and severity). Known expected issue on the Guest SSID: UNEXPECTED_CAPTIVE_PORTAL.

## Output formatting

```
STATUS <date time>  overall: GREEN | AMBER | RED
Platforms: ...            (one line, name anything unreachable)
Devices:   N online / M offline  (list offline)
Alarms:    ...            (critical/warn count, top item)
Changes:   ...            (last committed change + time; any pending)
UXI:       ...
Needs attention: - item (why)   [or "nothing"]
```

Keep it to this block. Add detail only when asked.

## Example

> "Jarvis, status update."
