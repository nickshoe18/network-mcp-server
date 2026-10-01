---
name: tenant-credential-sanity
title: Tenant and credential sanity check
description: |
  Confirm each platform connection on the lab MCP server points at the tenant it should, that no credentials
  from another tenant are present, and that secrets and container ports are locked down. Use after touching
  secrets, after a container change, when an API says "wrong org", or as a periodic check.
platforms: [mist, central, uxi, greenlake, clearpass]
tags: [security, tenant, credentials, isolation, audit, l1]
tools: [health, mist_list_org_networks, central_get_site_name_id_mapping, uxi_list_sensors, uxi_list_groups]
---

# Tenant and credential sanity check

## Objective

A credential that quietly points at the wrong tenant is a data-isolation failure. A stale customer token sat in the
lab secrets folder for weeks before it was noticed. This runbook catches that class of problem. Read-only, and it
never displays secret values.

## Hard rules

- Never `cat`, print, copy or paste any file under `secrets*/`, and never echo an environment variable holding a
  token. Check names, sizes and modification times only.
- You only have the LAB server. Customer tenants have their own isolated servers that are out of your scope.

## Procedure

### Step 1 - Reachability

`health()` for all platforms. Note which are unavailable and whether that is expected.

### Step 2 - Identity of each connection

- **Mist:** `mist_list_org_networks(org_id="5f24e447-1145-4efa-94e0-ccec1a2a00a7")`. Success means the token belongs
  to the Stark Industries org. An error saying "Wrong org_id ... correct org_id for this API token is X" means the
  token belongs to a different org: report it as a FAIL with the org id the message returned.
- **Central:** `central_get_site_name_id_mapping`. Expect only lab sites (Hall of Justice, Bat Cave, Sandbox
  Testing). Any other site name is a FAIL.
- **UXI:** `uxi_list_sensors` and `uxi_list_groups`. Expect the lab group and sensor. Report any other group name
  or sensor as "unexpected, confirm with the owner"; do not dig into it.
- **GreenLake / ClearPass / AOS8 / Axis:** confirm via `health` and the first identity-bearing call; report
  workspace or server names that do not match the lab inventory in CLAUDE.md.

### Step 3 - Secret hygiene (names only)

```
ls -la secrets/ | awk '{print $1, $5, $6, $7, $9}'
git check-ignore -v secrets/ secrets-srx/
git ls-files | grep -iE 'secret|token|\.pem|\.key' 
```
- Files under `secrets/` for platforms the lab does not use, or with modification dates that predate the lab's
  setup, deserve a question to the owner.
- The `git ls-files` command should return nothing tracked (example files are fine).

### Step 4 - Network exposure

```
docker ps --format '{{.Names}}  {{.Ports}}'
```
Every published port must be bound to `127.0.0.1`. Any `0.0.0.0` binding is a FAIL: the MCP servers have no
application-level authentication.

## Output formatting

A table: Area | Check | PASS/FAIL/UNVERIFIED | Observed. Then FAILs first, each with the impact and who
must act. Never include secret values, hashes or key material.

## Example

> "Do a tenant and credential sanity check."
