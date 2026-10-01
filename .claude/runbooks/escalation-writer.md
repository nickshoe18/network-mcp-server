---
name: escalation-writer
title: Write an escalation or support handoff
description: |
  Turn findings into a handoff another engineer or vendor support can act on without re-investigating: exact
  object and field to change, evidence, what was ruled out, impact, and rollback. Use whenever a runbook ends in
  "escalate", or when asked for a ticket, case, or handoff.
platforms: [mist, central, clearpass, srx]
tags: [escalation, ticket, handoff, support, l1]
tools: []
---

# Write an escalation or support handoff

## Objective

The next person should be able to act in five minutes. Be specific, ordered, and free of secrets.

## Format

**Title** - one line: what is broken and where.
**Impact** - who or what is affected, since when, and whether it is ongoing.
**Scope** - site, device names and MACs/serials, networks or VLANs, platform and software versions.
**Timeline** - timestamped events, oldest first (UTC), including any changes made and by whom if known.
**Evidence** - the exact commands or API calls and the relevant output, trimmed to the lines that matter.
**Ruled out** - what was checked and found healthy, so it is not repeated.
**Suspected cause** - with confidence (high/medium/low) and the evidence for and against.
**Requested action** - the exact object, field and value to change (for example "gateway template WAN_Template,
`port_config['ge-0/0/1-4'].networks` add `Guest`"), the risk, and how to roll back.
**Attachments** - anything to collect that only an engineer can (for example `request support information`).

## Rules

- Never include secrets: passwords, tokens, API keys, SSH keys, or password hashes. Refer to them by name only.
- Never include customer identity from other tenants.
- Quote errors verbatim. Keep raw output short; link or list the command instead of pasting pages.
- Separate facts you observed from inferences.

## Vendor support hints

- Juniper (SRX, EX, Mist): serial number, Junos version, the time window in UTC, and Mist device events with
  `config_diff` for any commit involved. The engineer runs `request support information` on the device.
- Aruba (Central, AOS8, ClearPass, UXI): device serial, firmware version, site, and the alert or event IDs.

## Output formatting

The block above, headed by the title. Keep it under one page.

## Example

> "Write this up for the Juniper engineer."
