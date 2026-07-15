"""Classic Central → canonical skeletal-role reader.

Confirmed (Central's own "Policy Configuration" documentation, plus
operator confirmation): the role object must exist in Central, named
exactly what ClearPass sends via the ``Aruba-User-Role`` RADIUS
attribute, before Central can match it against a policy. Central is
intent-based now (a policy can reference multiple roles), but it still
computes a "resultant role policy" per role internally regardless -- so a
faithful one-role-in-Classic-Central -> one-role-in-New-Central
translation (this reader) plus one matching policy (see ``policy.py``,
same name, referencing this role) is a correct, if not the most
consolidated, migration. Deliberately NOT attempting to merge multiple
Classic Central roles into a single shared-intent policy -- that's a
redesign a human should choose to do after a correct migration, not
something this tool should improvise.

Reuses ``CanonicalCentralProfile`` (the same generic shape the AAA-chain
kinds already use) rather than AOS 8's ``CanonicalRole`` -- that model is
gateway-specific (bandwidth contracts, session parameters); this is a
skeletal library role, created via the same generic
``central_write_profile`` writer already built.

Bridged-WLAN device-function guidance (per Central's docs, confirmed
this deployment is all-bridged): callers should pass
``device_functions=["CAMPUS_AP"]`` when writing these roles/policies, not
the switch/gateway defaults used elsewhere in this engine -- the reader
itself doesn't set this (readers never do; it's a writer_ctx the caller
supplies), but it's the correct choice for this deployment's roles.
"""

from __future__ import annotations

from typing import Any

from hpe_networking_mcp.translations.canonical.auth import CanonicalCentralProfile
from hpe_networking_mcp.translations.readers.classic_central._cli_parser import CliBlock, prop_str

_ROLES_PROFILE_TYPE = "roles"


def classic_central_read_skeletal_role(access_rule: CliBlock) -> CanonicalCentralProfile:
    """Build a skeletal Central role from one ``wlan access-rule <name>`` block.

    Args:
        access_rule: a block with ``keyword == "wlan access-rule"`` -- the
            same block ``classic_central_read_policy`` reads for its rules.
            The role name (``args[0]``) must match this reader's output
            for the pair to work together in Central.
    """
    name = (access_rule.get("args") or [""])[0]
    body: dict[str, Any] = {"name": name}
    vlan = prop_str(access_rule, "vlan")
    if vlan:
        body["vlan"] = vlan
    return CanonicalCentralProfile(kind="skeletal_role", profile_type=_ROLES_PROFILE_TYPE, name=name, body=body)
