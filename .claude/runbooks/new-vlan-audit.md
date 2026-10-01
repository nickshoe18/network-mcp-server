---
name: new-vlan-audit
title: End-to-end audit of a new or changed VLAN/network
description: |
  Verify a network is provisioned at every layer: network object, switch templates and trunks at both ends, AP
  port, WLAN, gateway interface/DHCP/policies/NAT, and the live devices. Use after adding a VLAN or SSID, or when
  a new network "half works". Audit only: reports gaps, never edits.
platforms: [mist, srx]
tags: [vlan, audit, provisioning, trunk, dhcp, l1]
tools: [mist_list_org_networks, mist_get_org_network_template, mist_get_org_gateway_template, mist_list_org_wlans, mist_search_site_sw_or_gw_ports]
---

# End-to-end audit of a new or changed VLAN/network

## Objective

Walk the whole chain and list every missing link with the exact object and field. The two gaps that broke the Guest
network for a full day were a VLAN missing from the switch uplink trunk and a DHCP DNS typo. Both are checked here.

## Prerequisites

The network name and VLAN ID (for example Guest, VLAN 3). SRX read-only CLI for Step 6.

## Checklist

Mark each PASS / FAIL / UNVERIFIED with the observed value.

1. **Network object** - `mist_list_org_networks`: name, `subnet`, `vlan_id`, `isolation`, `routed_for_networks`.
2. **Switch template** (`mist_get_org_network_template`):
   - The network is in the template's `networks` map with the same `vlan_id`.
   - It is in the `networks` list of EVERY port usage that must carry it: the AP usage, any host usage, and the
     UPLINK usage toward the gateway. Missing on the uplink is the classic gap.
   - Port usage names that apply to the relevant ports (`switch_matching` rules).
3. **WLAN** (`mist_list_org_wlans`): `vlan_id`, `bands`, `auth`, portal settings; no stale VLAN from an old WLAN.
4. **Gateway template** (`mist_get_org_gateway_template`):
   - `ip_configs.<net>` gateway IP inside the subnet.
   - `dhcpd_config.<net>` pool inside the subnet, gateway equals the IRB IP, DNS servers are real resolvers.
   - `port_config` LAN uplink `networks` list contains the network.
   - `service_policies`: the network is a tenant of the internet policy, and inter-network policies cover any
     required east-west access.
5. **Live switch** (`mist_search_site_sw_or_gw_ports`): the uplink port's `vlan_ids` includes the VLAN; the AP port
   too. Re-read after a minute if stale.
6. **Live SRX**:
   ```
   show vlans
   show interfaces irb terse
   show security zones <zone>
   show dhcp server binding
   ```
   IRB `up up` with the gateway IP; zone bound to the IRB; VLAN present on the LAN ports.
7. **Behavior**: one client per medium gets a lease from the right pool, resolves DNS, and reaches the internet.

## Output formatting

A table of the seven checks with PASS/FAIL/UNVERIFIED and the value seen, then a numbered list of FAILs, each with
the object, the field, and the value it should have. Do not make changes.

## Example

> "Audit the Guest network end to end."
