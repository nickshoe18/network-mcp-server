---
name: colorless-ports-deployment
title: Deploy colorless ports on AOS-CX — ClearPass RADIUS + Central port-profile build
description: |
  PRIMARY TRIGGER — invoke whenever the operator wants to build or roll out
  "colorless ports" / dynamic wired NAC on Aruba CX switches: every access
  port running the same 802.1X + MAC-Auth config, with ClearPass assigning
  the VLAN per device/user rather than the port being hand-configured.

  Match phrases include: "set up colorless ports", "build colorless ports",
  "dynamic wired NAC", "802.1X and MAC-auth on our switches", "RADIUS-based
  VLAN assignment on ports", "let ClearPass decide the VLAN", "wire up
  ClearPass with our CX switches for authentication", "roll out NAC to the
  wired ports", "same config on every port, let RADIUS pick the VLAN".

  This is a multi-session build spanning ClearPass (roles, enforcement
  profiles, role-mapping, services) and Aruba Central (RADIUS server,
  server-group, aaa-profile, switch-port-profile, scope assignment, and
  the actual per-port push). It embeds a live-verified gotcha ledger — the
  push-path bugs in this skill cost multiple debugging sessions to isolate
  the first time; do not rediscover them.

  **This is a WRITE skill** — every step past intake modifies live
  ClearPass and/or Central config. Confirm the intake answers with the
  operator before executing, and confirm before pushing config to any
  switch port carrying live traffic.
platforms: [clearpass, central]
tags: [clearpass, central, nac, radius, dot1x, mac-auth, vlan, colorless-ports]
tools:
  [
    clearpass_manage_network_device,
    clearpass_manage_role,
    clearpass_manage_enforcement_profile,
    clearpass_manage_role_mapping,
    clearpass_manage_enforcement_policy,
    clearpass_manage_service,
    clearpass_get_fingerprint_dictionary,
    clearpass_get_auth_sources,
    clearpass_compile_policy_flow,
    central_manage_auth_server,
    central_manage_auth_server_group,
    central_manage_aaa_profile,
    central_manage_sw_port_profile,
    central_manage_config_assignment,
    central_manage_interface_ethernet,
    central_get_scope_tree,
    central_resync_device_config,
    central_get_audit_logs,
    central_show_commands,
  ]
---

# Colorless ports on AOS-CX

## Objective

Build a working "colorless port" deployment: every targeted access port
runs an identical config (802.1X first, MAC-Auth fallback), and ClearPass
assigns the VLAN dynamically per device — via AD group for authenticated
users, via endpoint-profiling category for headless/MAC-Auth'd devices.
No port is ever hand-configured for "this is where the printer goes."

## Step 0 — Intake (ask before building anything)

Ask these up front. Don't guess at any of them — wrong answers here mean
rework on the live switch later, which is expensive on a stack carrying
real traffic.

1. **Target switch(es).** Site, switch model/stack, management IP or
   serial. Confirmed working pattern below is AOS-CX (verified on a CX
   6300 VSF stack, firmware FL.10.18.0001+). If the target is AOS-S or an
   older CX firmware, treat every "live-verified" claim below as unverified
   for that platform and expect to re-derive some of it.
2. **ClearPass reachability.** Confirm ClearPass is already a connected
   platform (`health` tool) and the operator has write access there.
3. **VLAN scheme.** What VLAN IDs already exist (or should be created) for
   each tier: Infrastructure/management, IoT, general users/employees,
   servers, guest, and a quarantine/fallback VLAN. Recommend reusing
   existing VLANs rather than inventing new ones.
4. **Enforcement model.** VLAN assignment via `Tunnel-Private-Group-Id`
   (recommended — simpler, no Dynamic Segmentation/UBT machinery needed)
   vs. downloadable user-role / UBT (more powerful, more moving parts).
   This skill's build steps assume VLAN assignment. If the operator wants
   role-based enforcement for per-role firewall policies in Central later,
   still build role-mapping granularity now (see step 4 below) — just
   route every role to the same VLAN today and repoint enforcement
   profiles later without touching role-mapping again.
5. **AD role differentiation (802.1X path).** Does the operator want
   distinct roles per AD group (e.g. Executive/Faculty/Student), or is a
   flat "anyone authenticated = Employee" sufficient? If AD groups: get
   the exact group names and confirm ClearPass already has a working AD
   auth source (`clearpass_get_auth_sources` — look for a non-system
   entry of `type: AD`). **Critical: default role for 802.1X should be
   `[Guest]`, not `[Employee]`** — defaulting to Employee silently grants
   full network-tier access to anyone who merely authenticates but isn't
   in a recognized group.
6. **MAC-Auth device categorization.** Which device tiers matter
   (Infrastructure / IoT / Servers / general computers / other) and which
   VLAN each should land on. **Never guess ClearPass's category strings**
   — pull the live fingerprint dictionary
   (`clearpass_get_fingerprint_dictionary`, paginate fully) or the live
   `clearpass_get_endpoints` profile data if the environment already has
   profiled devices, and use the exact strings found there. Common wrong
   guesses that silently fail (rule never matches, device falls to
   default — no error): `Access Point` → real is `Access Points`
   (plural); `Smart Device` → real is `SmartDevice` (no space, and this
   one alone can be 70%+ of a real device population); `IP Camera` → real
   is `Network Camera`; `Building Management System` → real is `Building
   Automation`. Ask specifically whether ambiguous categories like
   `Server`/`Computer` should get their own VLAN or fall to quarantine —
   these are real security decisions, not defaults to assume.
7. **Auth fallback.** 802.1X + MAC-Auth (recommended — MAC-Auth is what
   makes ports genuinely "colorless" for headless devices) vs. 802.1X
   only.
8. **Pilot scope.** Which specific ports to start on, and — critical —
   check `show interface brief` / existing VLAN trunk config first. A
   port that's already a trunk (e.g. serving an AP with multiple SSIDs'
   VLANs) will lose that trunk config if converted. Confirm with the
   operator whether pre-existing trunk ports are in scope or explicitly
   excluded.

## Procedure — ClearPass side

### Step 1 — Network Device

`clearpass_manage_network_device` (action `create`): register the switch
stack's management IP as a RADIUS client. Set `coa_capable: true`,
`coa_port: 3799`. Reuse the shared secret convention already in place for
other switches in this environment if one exists.

### Step 2 — Roles

`clearpass_manage_role`: one role per meaningful tier — e.g.
`Infrastructure`, `IoT`, `Servers`, `Quarantine`, plus one role per AD
group if step 0.5 called for it. Built-in `[Employee]` / `[Guest]` already
exist — reuse them, don't shadow them with a custom role of the same
name.

### Step 3 — Enforcement profiles (VLAN per role)

`clearpass_manage_enforcement_profile`, one per VLAN:

```json
{
  "name": "Colorless - <Tier> VLAN <id>",
  "type": "RADIUS",
  "action": "Accept",
  "attributes": [
    { "type": "Radius:IETF", "name": "Tunnel-Type", "value": "VLAN (13)" },
    { "type": "Radius:IETF", "name": "Tunnel-Medium-Type", "value": "IEEE-802 (6)" },
    { "type": "Radius:IETF", "name": "Tunnel-Private-Group-Id", "value": "<vlan id>" }
  ]
}
```

### Step 4 — Role-mapping policies (one per service, built in Step 6)

**802.1X role-mapping** — key on AD group membership:

```json
{
  "default_role_name": "[Guest]",
  "rule_combine_algo": "first-applicable",
  "rules": [
    {
      "match_type": "OR",
      "role_name": "<RoleName>",
      "condition": [
        { "type": "Authorization:<AuthSourceName>", "name": "memberOf", "oper": "CONTAINS", "value": "<ADGroupName>" }
      ]
    }
  ]
}
```

**Live-verified condition syntax gotcha:** the `type` field must match
the auth source's literal `name` exactly. Built-in sources
(`[Endpoints Repository]`, `[Guest Device Repository]`) have brackets
baked into their real name, so their condition type includes brackets —
`Authorization:[Endpoints Repository]`. A **custom** source you add
yourself (e.g. an AD source you named `Lab AD`) has no brackets in its
real name, so the condition type must be `Authorization:Lab AD` — no
added brackets. Getting this wrong produces a generic "condition type is
invalid" error that looks like a permissions problem, not a syntax one.
Also prefer the raw `memberOf` attribute with `CONTAINS` over the
`Groups` alias with `EQUALS` — `memberOf` holds full DNs and `CONTAINS`
matches the group CN directly, with no extra LDAP filter/join required.

**MAC-Auth role-mapping** — key on endpoint category, using the exact
strings confirmed in Step 0.6:

```json
{
  "default_role_name": "Quarantine",
  "rule_combine_algo": "first-applicable",
  "rules": [
    {
      "match_type": "OR",
      "role_name": "<RoleName>",
      "condition": [
        { "type": "Authorization:[Endpoints Repository]", "name": "Category", "oper": "EQUALS", "value": "<exact category string>" }
      ]
    }
  ]
}
```

### Step 5 — Enforcement policies (role → VLAN profile)

`clearpass_manage_enforcement_policy`, one per service: map each role
from Step 4 to its Step 3 profile, `default_enforcement_profile` set to
the quarantine/guest profile (never leave the default as a real-access
tier).

### Step 6 — Services (the 802.1X / MAC-Auth split)

Two RADIUS services, both scoped to the switch's NAD IP
(`Connection:NAD-IP-Address EQUALS <switch mgmt ip>`), differentiated by
the RADIUS `Service-Type` attribute — **live-verified**: MAC-Auth requests
always carry `Service-Type = Call-Check (10)`; 802.1X requests never do.

| Service | Extra rule | Auth methods | Auth sources |
|---|---|---|---|
| Wired 802.1X | `Service-Type NOT_EQUALS Call-Check (10)` | `[EAP PEAP]` | your AD source, `[Local User Repository]` |
| Wired MAC-Auth | `Service-Type EQUALS Call-Check (10)` | `[Allow All MAC AUTH]` | `[Endpoints Repository]` |

### Step 7 — Validate before touching a switch

`clearpass_compile_policy_flow` against each service, with fabricated
`simulated_attributes` covering every role-mapping branch (every AD group,
every device category, and the unmatched/default case). This is a
read-only simulation against the live policy engine — confirm every
branch resolves to the expected role → VLAN before any hardware step.

## Procedure — Central / switch side

### Step 8 — Auth-server

`central_manage_auth_server`: a single RADIUS server object pointing at
ClearPass's IP. Shared secret must match the Network Device from Step 1
exactly.

### Step 9 — Auth-server-group

`central_manage_auth_server_group`: wraps the server above.

**Live-verified gotcha — naming:** a server-group name containing a
**space** gets wholesale-rejected during Central's config push to this
switch type — not a field-level strip, the *entire group* silently
vanishes from what's pushed, which then leaves anything referencing it
(the aaa-profile, the port config) with a dangling reference. Use
underscores: `ClearPass_Servers`, not `ClearPass Servers`. This
reproduces even on a brand-new, minimal group — it is not about the
group's contents.

### Step 10 — AAA profile

`central_manage_aaa_profile`: `dot1x-auth` and `mac-auth` both enabled,
both `dot1xauth-server-group` / `macauth-server-group` set to the Step 9
group name.

### Step 11 — Switch-port profile

`central_manage_sw_port_profile`: access mode, the quarantine/pre-auth
VLAN, `aaa-profile` set to Step 10. **Live-verified gotcha:** the profile
must also include `dpi-enable: true` and a `flow-telemetry` block with an
exporter (copy the shape from an existing working port-profile in the
environment, e.g. an AP-port or server-port profile) — omitting these
causes the later per-port push to fail with a confusing, unrelated error
naming a device-fingerprinting module. It is not actually about
fingerprinting; it is a missing-field issue on the profile itself.

### Step 12 — Scope-assign everything

`central_manage_config_assignment` (action `assign`) for the Step 8 auth-
server, Step 9 server-group, and Step 11 port-profile — each needs an
explicit site + device-function scope assignment. **Live-verified
gotcha:** creating these objects in Central's shared library is not
enough for them to reach a specific device. An unassigned object can even
*appear* briefly on the device after a push and then silently disappear
once Central notices nothing actually references it in that scope.

### Step 13 — Apply the port-profile to interfaces

`central_manage_interface_ethernet` (action `update`), payload
`{"name": "<port>", "sw-profile": "<Step 11 profile name>", "routing": false}`.

**Live-verified gotcha — the single biggest time sink in this whole
build:** the correct field is **`sw-profile`**, not `profile-name`. Tool
schema references may list `profile-name` — it is wrong for this
purpose. Using it produces a 500 error naming an unrelated module
(`aruba-devicefingerprinting-profile`) that has nothing to do with the
actual problem. If a port-profile push ever fails with that exact error
text, check the field name first before investigating anything else.

### Step 14 — Push and validate

1. `central_resync_device_config` to trigger the push.
2. `central_show_commands` → `show running-config`, and check the actual
   interface/aaa lines directly. This is ground truth — nothing else is.
3. `central_get_audit_logs`, filter for `Config eliminated` entries naming
   your specific objects. **A "success" / `configStatus: SYNCHRONIZED"`
   push can still have silently eliminated the one object you care about**
   — status alone is not proof.
4. `central_show_commands` → `show radius-server` on the switch confirms
   whether the ClearPass server is actually live and reachable
   (unreachable servers are prefixed with `*`).

## Decision matrix

| Situation | Action |
|---|---|
| Port-profile push fails naming `aruba-devicefingerprinting-profile` | Check the payload field is `sw-profile`, not `profile-name` (Step 13); if that's already correct, check the profile itself has `dpi-enable` + `flow-telemetry` (Step 11) |
| Auth-server-group vanishes from `Config eliminated` audit entries | Check the group name for spaces — rename with underscores (Step 9) |
| A newly-created auth-server/server-group/port-profile never reaches the device | Confirm it was scope-assigned (Step 12), not just created |
| ClearPass role-mapping condition rejected as "invalid type" | Check whether the auth source is custom (no brackets in condition type) vs. built-in (brackets included) |
| Push reports "success" but the port's config didn't change | Don't trust `configStatus` alone — pull `show running-config` and check the audit log for eliminations on that specific push cycle |
| Target switch firmware predates the currently-installed version | An unsupported/eliminated field may cause the *entire* push to fail outright rather than degrade gracefully; a firmware upgrade can change this failure mode without fixing an underlying naming/field issue — don't conflate the two |

## Output formatting

After the build, report back:

- A table of role → VLAN mapping actually configured (both services).
- Confirmation via `clearpass_compile_policy_flow` simulation results for
  every branch.
- Confirmation via live `show running-config` + `show radius-server` for
  every pushed port — not just a "push succeeded" claim.
- Any decision points from Step 0 that were assumed rather than
  explicitly confirmed by the operator, flagged for follow-up.

## Example

> "Let's set up colorless ports on the new CX stack at the Rockwall site"
> "Build out dynamic wired NAC through ClearPass for our access switches"
