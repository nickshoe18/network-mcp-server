---
name: hygiene-audit
title: Lab hygiene audit - firmware, certificates, admin activity, inventory drift
description: |
  Periodic read-only check of firmware compliance, device certificate expiry, direct-login and admin activity,
  and drift between live inventory and the project docs. Use for "anything I should worry about", "audit the lab",
  or on a schedule.
platforms: [mist, central]
tags: [audit, firmware, certificates, hygiene, inventory, l1]
tools: [mist_get_site_switches_metrics, mist_get_site_gateway_metrics, mist_list_org_devices_stats, mist_search_site_device_events, mist_list_org_audit_logs, mist_search_org_inventory]
---

# Lab hygiene audit

## Objective

Surface things that will bite later: out-of-date firmware, certificates near expiry, unexpected admin activity,
and inventory that no longer matches the documentation. Read-only.

## Procedure

### Step 1 - Firmware compliance

`mist_get_site_switches_metrics(site_id)` and `mist_get_site_gateway_metrics(site_id)`: `version_compliance` score
and the major version in use. For APs, read `version` from `mist_list_org_devices_stats(org_id, type="ap")`.
Report versions; upgrades are an escalation.

### Step 2 - Certificate expiry

`mist_list_org_devices_stats(org_id)` returns `cert_expiry` (epoch seconds) per device. Days left =
(`cert_expiry` - `last_seen`) / 86400. Flag anything under 60 days. Do the arithmetic in the sandbox with integers
(`datetime.fromtimestamp` is unavailable).

### Step 3 - Admin and direct-login activity

- `mist_list_org_audit_logs(org_id, duration="7d")`: who changed what; group by administrator and message.
  Flag changes to gateway/switch templates and any deletion.
- `mist_search_site_device_events(site_id, mac=<gateway mac>, duration="7d")`: `GW_NON_MIST_USER_LOGIN` means
  someone logged into the SRX CLI directly. List the times; the owner can confirm they were expected.

### Step 4 - Inventory drift

`mist_search_org_inventory(org_id)` and Central's device list against the inventory in CLAUDE.md. Report devices
present but undocumented, and documented but missing/offline. Do not edit CLAUDE.md; report the differences.

### Step 5 - Known local exceptions

Note, do not fix: the read-only `claude-ro` SRX login and the `netops` login exist by design; a dashboard save of
the gateway template can silently drop API-only fields (for example `protect_re`), so re-read the template if a
change seems to have vanished.

## Output formatting

Sections Firmware / Certificates / Activity / Drift, each PASS or a short list of findings with values. End with
a prioritized "worth attention" list of at most five items.

## Example

> "Run the lab hygiene audit."
