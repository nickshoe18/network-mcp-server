---
name: slow-wifi
title: Slow, unstable, or poor Wi-Fi
description: |
  Triage complaints of slow Wi-Fi, drops, or roaming problems using Mist SLE, AP radio statistics, client signal,
  and UXI. Use for "Wi-Fi is slow", "keeps dropping", "bad signal in the lab".
platforms: [mist, uxi, central]
tags: [wifi, rf, sle, performance, roaming, l1]
tools: [mist_list_site_sles_metrics, mist_get_site_sle_summary_trend, mist_list_org_devices_stats, mist_search_site_wireless_clients, uxi_get_sensor_status]
---

# Slow, unstable, or poor Wi-Fi

## Objective

Separate RF/capacity problems from client problems and from upstream (WAN/DNS) problems that only look like
Wi-Fi problems.

## Procedure

### Step 1 - Is it Wi-Fi at all?

If wired clients are also slow, or `CLIENT_DNS_OK` is missing, run `internet-wan-down` first.

### Step 2 - SLE

**Tools:** `mist_list_site_sles_metrics(site_id, scope="site", scope_id=<site_id>)` to see available metrics, then
`mist_get_site_sle_summary_trend(site_id, scope="site", scope_id=<site_id>, metric=<metric>)` for coverage,
capacity, roaming, time-to-connect and throughput. Low values name the failing dimension.
Note: with a single AP, roaming SLE is not meaningful.

### Step 3 - AP radios

`mist_list_org_devices_stats(org_id, type="ap", mac=<no colons>)` and read `radio_stat` per band:
`util_all`, `util_non_wifi`, `num_clients`, `channel`, `bandwidth`, `power`, `noise_floor`.
High `util_non_wifi` (especially 2.4 GHz) is interference. `power_constrained: true` means the AP is not getting
enough PoE and radios are reduced: check the switch port budget.

### Step 4 - The client

`mist_search_site_wireless_clients(site_id, ...)` (fuzzy `*` supported on mac/hostname): RSSI, band, protocol,
streams. RSSI worse than about -70 dBm is a coverage problem. Note the Guest WLAN broadcasts only on 5 and 6 GHz;
2.4-only clients cannot join it.

### Step 5 - Independent measurement

`uxi_get_sensor_status` and UXI issues for the lab sensor: a UXI issue at the same time corroborates a real
problem rather than one client's.

## Decision matrix

| Finding | Likely cause | Action |
|---|---|---|
| Coverage SLE low or RSSI < -70 | Distance/obstruction | Report location; escalate AP placement |
| Utilization high on a band | Congestion or interference | Report channel and utilization |
| `power_constrained` | PoE budget | Check the switch port and cable |
| SLE fine, one client slow | Client driver/band | Test another device |

## Output formatting

Jarvis ticket format with the SLE values and radio numbers in Findings.

## Example

> "Wi-Fi in the lab is really slow this afternoon."
