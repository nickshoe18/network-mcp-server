---
name: dhcp-troubleshooting
title: DHCP is not answering on a VLAN
description: |
  Trace why clients on one VLAN get no lease: is the network defined and provisioned on the gateway, does the
  VLAN reach the gateway across every trunk, and is the DHCP server actually offering. Use after a client
  shows DHCP failures, a 169.254 address, or "DISCOVER" with no "ACK".
platforms: [mist, srx]
tags: [dhcp, vlan, trunk, srx, l2, l1]
tools: [mist_list_org_networks, mist_get_org_gateway_template, mist_get_org_network_template, mist_search_site_sw_or_gw_ports, mist_search_site_wired_clients]
---

# DHCP is not answering on a VLAN

## Objective

Find which link in the chain is missing: gateway network definition -> switch trunks at both ends ->
frames arriving at the gateway -> DHCP server offering. Work top to bottom and stop at the first break.

## Prerequisites

- The VLAN or network name (for example Guest, VLAN 3) and a client that is failing.
- SRX read-only CLI available (see Jarvis prompt). All commands here are `show`.

## Procedure

### Step 1 - Is the network provisioned on the gateway?

**Tools:** `mist_list_org_networks(org_id)`, `mist_get_org_gateway_template(org_id, gatewaytemplate_id)`
**Check in the gateway template:** `ip_configs.<net>` (gateway IP), `dhcpd_config.<net>` (pool, gateway, DNS),
and that `<net>` is in `port_config[<lan uplink>].networks`.
**Sanity-check the values:** DNS server addresses that are not real resolvers (a typo such as 4.4.4.4 instead of
8.8.4.4 causes secondary-DNS failures), a pool outside the subnet, a gateway not equal to the IRB address.
**If anomaly:** escalate the exact field; L1 does not edit templates.

### Step 2 - Does the VLAN cross every switch trunk?

**Tools:** `mist_get_org_network_template` (port usages), `mist_search_site_sw_or_gw_ports(site_id, mac, port_id)`
**Check:** the network is in the `networks` of BOTH the client-side usage (for example `AP_Port`) AND the uplink
usage toward the gateway (for example `Uplink_Port`). Then confirm live: the uplink port's `vlan_ids` must contain
the VLAN. Port stats lag a minute after a change - re-read before concluding.
**A common miss:** VLAN added on the access/AP side but not on the uplink trunk.

### Step 3 - Are frames reaching the gateway? (SRX CLI)

```
show vlans
show interfaces irb terse
show ethernet-switching table vlan-name <VLAN>
```
- IRB for the VLAN must be `up up` with the gateway IP.
- Empty MAC table for the VLAN = no frames arriving = trunk problem (Step 2), not DHCP.
- Client MAC present on the LAN port = frames arrive; go to Step 4.

### Step 4 - Is the DHCP server offering?

```
show dhcp server binding
show dhcp server statistics
```
- Binding entry on the right `irb.N` for the client MAC = it got a lease.
- Statistics: DHCPDISCOVER received vs DHCPOFFER sent. Equal with 0 dropped means the server is healthy and the
  problem is upstream (Steps 2-3). Discovers rising with offers flat means a server or pool problem: escalate.

### Step 5 - Isolate wired vs wireless

If wireless fails, a wired device on the same VLAN removes the AP/WLAN from the picture. Use only an authorized
temporary port override, and say it must be removed afterwards.

## Decision matrix

| Finding | Likely cause | Action |
|---|---|---|
| Network/DHCP scope missing in gateway template | Never provisioned | Escalate (template edit) |
| VLAN missing on uplink trunk | Trunk gap | Escalate (switch template edit), name the exact usage |
| IRB down or absent | Gateway side not provisioned | Escalate |
| MAC table empty, trunks correct | Frames lost between switch and SRX | Check port up state and cabling |
| Discovers = offers, client still fails | Return path or client side | Check AP/WLAN VLAN, client behavior |

## Notes

- `mist_show_site_device_dhcp_leases` returns only a websocket session id, not the lease list. Use the SRX CLI.
- Releasing a lease (`mist_release_site_device_dhcp_lease` with `network` and `macs`) is a write action and needs
  explicit authorization.

## Output formatting

Jarvis ticket format. Findings must name the failing link (Steps 1-4) with the value you observed.

## Example

> "Devices on VLAN 3 aren't getting addresses."
