---
name: cannot-reach-destination
title: Host A cannot reach host B (inter-VLAN or to the gateway itself)
description: |
  Trace why traffic from one host or network to another fails: routing, gateway zone policy, policy-based routing,
  NAT, and traffic destined to the SRX's own addresses (SSH, ping). Use for "can't ping X", "can't SSH to the
  SRX", "VLAN A can't reach VLAN B", "server not reachable from Wi-Fi".
platforms: [mist, srx]
tags: [reachability, inter-vlan, routing, policy, srx, l1]
tools: [mist_search_site_wired_clients, mist_get_org_gateway_template, mist_list_org_networks, mist_search_site_device_events]
---

# Host A cannot reach host B

## Objective

Decide which hop drops the traffic: source client, path to the gateway, gateway routing/policy, or the destination.
"Never arrived" and "arrived and was dropped" look identical to the user; separate them.

## Prerequisites

- Source IP and network, destination IP and network, protocol/port, and the exact failure (timeout vs refused).
- SRX read-only CLI (see Jarvis prompt). To test, use the "Active tests" methods in the Jarvis prompt: the
  `.claude/tools/mist_device_cmd.py` helper for ping/traceroute from the switch, AP or gateway, or `ping` on the
  SRX CLI. The Mist MCP ping tools themselves return output only over a websocket and are not usable directly.

## Procedure

### Step 1 - Classify the destination

- Destination is the SRX's own IP (10.x.x.1 gateway, management)? Go to Step 6; flow sessions will not show it.
- Destination is another host: continue.

### Step 2 - Source is healthy and on the right network

Confirm the source has an address in the expected subnet and a working gateway (run the `client-cannot-connect`
runbook if not).

### Step 3 - Route and address resolution on the SRX

```
show route <destination-ip>
show arp | match <destination-ip>
```
The destination subnet must be a direct route on an `irb.N` (or via a routing instance). No ARP entry for a host on
a directly connected subnet means it is not answering or not on that VLAN.

### Step 4 - Is a session created?

```
show security flow session source-prefix <src> destination-prefix <dst>
```
- Session present, packets in both directions: the SRX permitted and forwarded it; the problem is the destination
  or return path.
- Session present, packets only outbound: destination not answering (host firewall, wrong VLAN, down).
- No session: never arrived, or denied before session creation. Go to Step 5.

### Step 5 - Policy and steering

**Mist side:** `mist_get_org_gateway_template` - is there a `service_policies` entry whose `tenants` include the
SOURCE network and whose `services` cover the DESTINATION network? Mist networks are isolated by default; a
`Policy-1`-style internet policy does not permit east-west traffic. Check `path_preferences` for the destination
network, and `mist_list_org_networks` for `isolation` / `routed_for_networks`.
**SRX side:** `show security policies from-zone <SRC-ZONE> to-zone <DST-ZONE>` for a permit; `show security zones
<zone>` for the interface binding. If the CLI denies the command, escalate with what you have.

### Step 6 - Traffic to the SRX itself (SSH, ping, HTTPS to the box)

Flow sessions do not appear for self-destined traffic. Test from the source and read the behavior:
- Timeout: silently dropped. Two layers can do this: the zone's `host-inbound-traffic system-services` (must list
  the service for the ingress zone) and the `protect_re` filter on `lo0`.
- Connection refused: the service is not running or actively rejected.
- Banner missing after TCP connects: device mid-commit, retry in a minute.
The zone service lines are applied through the gateway template's `additional_config_cmds`; `protect_re` scoping
must use `custom` entries, not `allowed_services`. Both are escalations.

## Decision matrix

| Finding | Likely cause | Action |
|---|---|---|
| No route / no ARP for destination | Wrong VLAN, host down, gateway interface missing | Check destination port VLAN (`find-device`) |
| No session, no matching policy | Missing inter-network service policy | Escalate the exact template change |
| Session out only | Destination or host firewall | Ask the owner to check the host |
| Self-destined timeout | Zone service or protect_re | Escalate with the ingress zone name |

## Output formatting

Jarvis ticket format; Findings names the hop where it stops.

## Example

> "I can't SSH to the SRX from the Wi-Fi network."
