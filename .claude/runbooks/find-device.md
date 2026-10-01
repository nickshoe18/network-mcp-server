---
name: find-device
title: Find where a device is (by MAC, IP, or name)
description: |
  Locate any client or device: which site, switch port or AP/SSID, VLAN, IP and lease, and when it was last seen.
  Use for "where is device X", "what is on this IP", "who has 192.168.103.50", "what's plugged into port N".
platforms: [mist, central, clearpass, srx]
tags: [inventory, lookup, mac, ip, client, l1]
tools: [find_mist_entity, mist_search_org_wireless_clients, mist_search_org_wired_clients, mist_search_site_wan_clients, mist_search_site_wired_clients, mist_search_org_inventory]
---

# Find where a device is

## Objective

Return one row per match with: name, MAC, IP, VLAN/network, attachment point (port or AP + SSID), and last seen.

## Procedure

### Step 1 - One call across everything

**Tool:** `find_mist_entity(org_id, query="<mac|ip|name prefix>")` (juniper-mist-official). It fans out across
wireless, wired, WAN and NAC clients, inventory and guests, and returns the entity type, site and MAC. Use `entity_types`
to narrow. MAC in any notation works; names are prefix-matched.

### Step 2 - Detail by type

- Wireless: `mist_search_org_wireless_clients(org_id, ip=|mac=|hostname=)` - AP, SSID, band, VLAN, IP.
- Wired: `mist_search_org_wired_clients` / `mist_search_site_wired_clients(site_id, port_id=)` - `device_mac_port`
  gives switch and port; `source: lldp` entries are infrastructure (AP, gateway); `source: mac` is a learned host.
- Behind the gateway: `mist_search_site_wan_clients`.
- Infrastructure: `mist_search_org_inventory(org_id, text=<name/serial>)`.
- Aruba Central devices: `central_find_device` / `central_get_devices`.

### Step 3 - Cross-check on the SRX

```
show dhcp server binding
show arp | match <ip-or-mac>
show ethernet-switching table
```
The lease table maps IP to MAC and interface (irb.N); the MAC table shows which LAN port it was learned on.

### Step 4 - Nothing found

Widen the time window; the client may be offline. A MAC that never appears may be a randomized address; ask the
operator for the device's address for this specific network.

## Output formatting

A small table:

| Name | MAC | IP | Network/VLAN | Attached to | Last seen |

Then one line on anything odd (duplicate IP, randomized MAC, stale lease).

## Example

> "Who has 192.168.103.50?"
