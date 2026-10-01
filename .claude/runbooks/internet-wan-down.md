---
name: internet-wan-down
title: Internet or WAN is down or only one network has no internet
description: |
  Triage loss of internet access: the WAN link, the ISP-facing interface, default route, DNS, or a single
  network missing its internet policy or NAT. Use for "no internet", "everything is offline", "only Guest has no
  internet".
platforms: [mist, srx, uxi]
tags: [wan, internet, dns, nat, srx, l1]
tools: [mist_list_org_devices_stats, mist_search_site_sw_or_gw_ports, mist_search_site_device_events, mist_get_org_gateway_template, uxi_get_sensor_status]
---

# Internet or WAN is down

## Objective

First decide scope: ALL networks or ONE. All networks points at the WAN link, ISP, default route or DNS. One
network points at that network's policy, NAT or DHCP DNS settings.

## Procedure

### Step 1 - Scope

Check a client on two different networks (for example Wireless_Users and Wired_Users). Client events showing
`CLIENT_DNS_OK` mean the path to DNS works; a client with an IP but no DNS success points at DNS or WAN.

### Step 2 - Gateway and WAN port

**Tools:** `mist_list_org_devices_stats(org_id, type="gateway", mac=<no colons>)` (status, `ext_ip`, uptime);
`mist_search_site_sw_or_gw_ports(site_id, mac=<gateway mac>, port_id="ge-0/0/0")` (up, speed, errors).
`ext_ip` changing means the ISP address changed.

### Step 3 - SRX WAN state (read-only CLI)

```
show interfaces ge-0/0/0 terse
show route 0.0.0.0/0
show dhcp client binding
show services rpm probe-results
show security flow session destination-prefix 8.8.8.8
```
- Interface up but no default route or no DHCP lease: ISP/modem side.
- Route present, RPM probe (8.8.8.8) failing: upstream loss.
- Sessions to 8.8.8.8 with packets outbound only: return traffic not coming back (NAT, ISP).

### Step 4 - One network only

`mist_get_org_gateway_template`: the network must be in `service_policies` for the internet policy's `tenants`
(the internet-bound policy), and DHCP `dns_servers` must be real resolvers (a typo such as 4.4.4.4 breaks the
secondary). A network missing from the internet policy gets no internet and no error. Escalate the exact field.

### Step 5 - Corroborate with UXI

`uxi_get_sensor_status` for the lab sensor: connectivity or DNS issues on its networks confirm the outage
independently of Mist.

## Decision matrix

| Finding | Likely cause | Action |
|---|---|---|
| WAN port down or no lease | Modem/ISP/cable | Ask the operator to check the modem and cable |
| WAN up, no default route | DHCP failure from the ISP | Escalate to the ISP; report `ext_ip` history |
| All networks fail, WAN healthy | DNS or policy | Check DNS test and the internet policy |
| One network fails | Missing policy/NAT/DNS scope | Escalate the template field |

## Output formatting

Jarvis ticket format; state the scope (all vs one network) in the first Findings bullet.

## Example

> "Guest Wi-Fi connects but nothing loads."
