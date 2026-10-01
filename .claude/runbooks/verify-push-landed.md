---
name: verify-push-landed
title: Verify a configuration push actually reached the device
description: |
  After a template or config change, confirm the intended change was committed to the device, is still in effect,
  and did not silently revert. Use for "did it push", "is it live yet", "it worked then stopped". Read-only.
platforms: [mist, srx]
tags: [change, commit, verification, config, l1]
tools: [mist_search_site_device_events, mist_get_org_gateway_template, mist_get_org_network_template, mist_search_site_sw_or_gw_ports, mist_list_org_devices_stats]
---

# Verify a configuration push landed

## Objective

A saved template is only the desired state. This runbook proves what the device actually has.

## Procedure

### Step 1 - Was it queued and committed?

`mist_search_site_device_events(site_id, mac=<no colons>, duration="1h")` for the target device.
- Gateway: `GW_CONFIG_CHANGED_BY_USER` (queued) then `GW_CONFIGURED` with a `config_diff` (committed).
- Switch: `SW_CONFIG_CHANGED_BY_USER` then `SW_CONFIGURED` (`UI_COMMIT_COMPLETED`).
- The SRX needs about 4 minutes; the switch about a minute. Junos commits are "commit confirmed, rollback in 10
  mins"; Mist confirms them, but a later diff that reverses yours means it rolled back or was overwritten.

### Step 2 - Does the diff contain what was intended?

Search the `config_diff` for the specific stanza (a zone name, a user, a prefix-list, a term name). A commit that
only shows NTP-server changes is routine housekeeping and does NOT include your change. Mask password hashes and
keys when quoting a diff.

### Step 3 - Is the desired state still what you expect?

Re-read the template (`mist_get_org_gateway_template` / `mist_get_org_network_template`) and compare the field.
Compare `modified_time` with the commit time. A full-body save from another editor (including the dashboard) can
drop API-only fields; if the field vanished, look for who saved last in `mist_list_org_audit_logs`.

### Step 4 - Live effect

- Switch: `mist_search_site_sw_or_gw_ports(site_id, mac, port_id)` - `vlan_ids`, `up`, `stp_state`. Stats lag;
  re-read after a minute.
- SRX: the relevant `show` command (`show vlans`, `show interfaces irb terse`, `show dhcp server binding`).
- Then one behavioral test from a client.

### Step 5 - Pending too long?

A `*_CONFIG_CHANGED_BY_USER` with no `*_CONFIGURED` for more than 10 minutes is stuck. Check the device is
connected and its `module_stat[].status` (a gateway can show connected at the top level while its management
module is disconnected). Escalate with the timestamps.

## Decision matrix

| Finding | Meaning | Action |
|---|---|---|
| Queued, not committed, under 10 min | Normal delay | Wait and re-check |
| Committed, diff lacks your stanza | Change not generated | Escalate: template field may not map to config |
| Committed, then reversed | Rollback or overwrite | Check audit logs; escalate |
| Template field missing | Overwritten by another save | Escalate with the audit entry |

## Output formatting

Jarvis ticket format. State plainly: "queued / committed / confirmed live / reverted", with timestamps.

## Example

> "Did the SSH change on the SRX push?"
