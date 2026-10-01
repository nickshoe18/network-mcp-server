---
name: marvis-review
title: Review Marvis actions, alarms, and Marvis client events
description: |
  Pull the current Marvis findings for the lab: active Marvis Actions (proactive detections and Marvis Minis
  connectivity tests), Mist alarms, and Marvis-tagged client events, then summarize what is new and what needs a
  human. Use for "what's Marvis saying", "any alerts", "anything new in Mist".
platforms: [mist]
tags: [marvis, alerts, alarms, minis, monitoring, l1]
tools: [get_mist_insights, mist_search_org_alarms, mist_search_site_alarms, mist_search_site_wireless_client_events, mist_troubleshoot_org]
---

# Review Marvis actions, alarms, and client events

## Objective

Report what Marvis and Mist alarms currently flag, ranked by severity, and separate real problems from noise.
Read-only. This is a pull: nothing here notifies you on its own.

## Procedure

### Step 1 - Marvis Actions (primary source)

**Tool:** `get_mist_insights(insight_type="marvis_actions", org_id=..., params={"active": true})` on the
`juniper-mist-official` connection. Optional params: `category`, `priority`, `status`, `symptom`. It returns
prioritized issues across connectivity, wired, wireless, AP, switch and gateway, and includes Marvis Minis results
(proactive DHCP, ARP, DNS and application reachability tests). No time range applies; it lists what is currently
active.
**If the connection is down:** that server can be disconnected while the rest works. Say so, use Steps 2-3, and
report "Marvis Actions: unavailable".

### Step 2 - Alarms

`mist_search_org_alarms(org_id, duration="1d")`. Group by `group` (infrastructure / marvis / security), severity and
type. Report critical and warn; count the rest.

### Step 3 - Marvis-tagged client events

`mist_search_site_wireless_client_events(site_id, duration="1h")` and keep events whose `type` starts with
`MARVIS_EVENT_` (for example `MARVIS_EVENT_CLIENT_DHCP_FAILURE`, `..._AUTH_FAILURE`, `..._CAPTIVE_PORTAL_...`).
Count by type and by client; a burst from one client is usually that client, not the network.

### Step 4 - Drill into one client if asked

`mist_troubleshoot_org(org_id, site_id, mac=<no colons>, type="client")`. Its recommendations are generic
boilerplate; treat them as a lead, never as root cause.

## Interpreting

- A Marvis Action is a detection, not a proven root cause. Verify with the relevant runbook before acting.
- Known lab noise: DFS radar events on some channels, and routine gateway firmware messages.
- `UNEXPECTED_CAPTIVE_PORTAL` from the UXI sensor on the Guest SSID is expected while the portal is enabled.
- The same finding repeating across days is worth an escalation even if minor.

## Output formatting

```
MARVIS <date time>
Actions:  N active (top: <category> - <one-line>)   | unavailable
Alarms:   critical N, warn N (top: <type> - <where>)
Events:   <count of MARVIS_EVENT_* by type, top client>
New since last look: <items>   [only if known]
Needs a human: - item (why)   [or "nothing"]
```

## Example

> "Jarvis, any Marvis alerts?"
