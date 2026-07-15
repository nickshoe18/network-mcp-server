"""Classic Central → canonical security-policy reader.

Builds a ``CanonicalPolicy`` from one ``wlan access-rule <name>`` block.
Confirmed relationship (operator-confirmed + Central's own "Policy
Configuration" docs): the role object must already exist in Central with
a name matching what ClearPass sends via the ``Aruba-User-Role`` RADIUS
attribute for the role to be assigned correctly. So the access-rule's own
name (the block's ``args[0]``) IS the role name, and this reader produces
the policy that governs it (see ``role.py`` for the matching skeletal
role object -- a separate, smaller translation).

New Central is intent-based (one policy can reference many roles,
avoiding duplication) where Classic Central was role-centric (each role
carried its own ACL, this reader's exact source shape). This reader
deliberately does the *faithful* translation -- one policy per Classic
Central role, referencing only that role -- rather than attempting to
consolidate several roles into a shared-intent policy. That's correct,
not just expedient: Central still computes a "resultant role policy" per
role internally regardless of which style built it, so this produces the
right enforced behavior; consolidating into fewer intent-based policies
is a redesign a human should choose to do after a correct migration, not
something this tool should improvise.

Grammar (confirmed from two real Wayne Enterprises examples + generalized,
not hardcoded to those specific values):
``rule <dest-type> <dest-value> match <protocol> <port-start> <port-end> <action>``
where ``dest-type`` is ``any`` (paired with ``dest-value=any``, no filter),
``alias <net-group-name>``, or ``masterip <ip>``; ``protocol`` is ``any``,
``tcp``, or ``udp``; ``action`` is ``permit``/``deny``/``redirect``.
The implicit *source* of every rule is the role itself (this is a
role-bound ACL, not an interface ACL -- matches AOS 8's role-injection
pattern for a bare ``any`` side, except here the association is always to
THIS block's own role, never inferred from a separate role reverse-index).

Scope note (caller's responsibility, not this reader's): wired-port-profile
access-rules (referenced by a ``wired-port-profile`` block's
``access-rule-name`` property) are port-level, not role-level, and are out
of scope per the colorless-ports decision (see project memory) -- the
caller should exclude any access-rule block whose name is referenced that
way before calling this reader, rather than this reader guessing from a
hardcoded name list (that would violate the "generic, not tenant-specific"
design requirement).

An action with no Central mapping fails closed to ``ACTION_DENY`` (never a
silent ``ACTION_ALLOW`` fall-through) and is recorded in
``unmapped_actions`` -- same discipline as the AOS 8 policy reader.
"""

from __future__ import annotations

from typing import Any

from hpe_networking_mcp.translations.canonical.policy import CanonicalPolicy
from hpe_networking_mcp.translations.readers.classic_central._cli_parser import CliBlock, prop_all

_ACTION_TO_CENTRAL: dict[str, str] = {
    "permit": "ACTION_ALLOW",
    "deny": "ACTION_DENY",
    "redirect": "ACTION_REDIRECT",
}


def _dest_address(dest_type: str, dest_value: str) -> dict[str, Any]:
    if dest_type == "alias":
        return {"type": "ADDRESS_ALIAS", "net-group": dest_value}
    if dest_type == "masterip":
        return {"type": "ADDRESS_HOST", "host-address": {"host-ipv4-address": dest_value}}
    # "any", or any unrecognized dest-type -- widen the match scope to ANY.
    # Safe direction to degrade in: it only broadens what a rule MATCHES,
    # never changes the rule's ALLOW/DENY action, so an unknown dest-type
    # can't turn a deny into an allow (unlike the action fallback below,
    # which fails closed for exactly that reason).
    return {"type": "ADDRESS_ANY"}


def _protocol_block(protocol: str, port_start: str | None, port_end: str | None) -> tuple[str, dict[str, Any] | None]:
    proto_enum = {"tcp": "IP_TCP", "udp": "IP_UDP"}.get(protocol)
    if proto_enum is None:
        return "RULE_ANY", None
    block: dict[str, Any] = {"ip-header": {"protocol": proto_enum}}
    if port_start not in (None, "any"):
        min_port = int(port_start)  # type: ignore[arg-type]
        if port_end not in (None, "any") and int(port_end) != min_port:  # type: ignore[arg-type]
            block["transport-fields"] = {
                "destination-port": {"operator": "COMPARISON_RANGE", "min": min_port, "max": int(port_end)}  # type: ignore[arg-type]
            }
        else:
            block["transport-fields"] = {"destination-port": {"operator": "COMPARISON_EQ", "min": min_port}}
    rule_type = "RULE_TCP" if proto_enum == "IP_TCP" else "RULE_UDP"
    return rule_type, block


def _build_rule(role_name: str, tokens: list[str], position: int, unmapped: list[str]) -> dict[str, Any] | None:
    if "match" not in tokens:
        return None  # doesn't match the expected grammar (e.g. a 'route' policy rule) -- skip, don't guess
    match_idx = tokens.index("match")
    dest_tokens, rest = tokens[:match_idx], tokens[match_idx + 1 :]
    if len(dest_tokens) < 2 or len(rest) < 4:
        return None

    dest_type, dest_value = dest_tokens[0], dest_tokens[1]
    protocol, port_start, port_end, action_word = rest[0], rest[1], rest[2], rest[3]

    rule_type, proto_block = _protocol_block(protocol, port_start, port_end)
    central_action = _ACTION_TO_CENTRAL.get(action_word)
    if central_action is None:
        unmapped.append(action_word)
        central_action = "ACTION_DENY"  # fail-closed

    condition: dict[str, Any] = {
        "rule-type": rule_type,
        "address-family": "IPV4",
        "source": {"type": "ADDRESS_ROLE", "role-list": [role_name]},
        "destination": _dest_address(dest_type, dest_value),
    }
    if proto_block:
        condition.update(proto_block)
    return {"position": position, "condition": condition, "action": {"type": central_action}}


def classic_central_read_policy(access_rule: CliBlock) -> CanonicalPolicy:
    """Build a ``CanonicalPolicy`` from one ``wlan access-rule <name>`` block.

    Args:
        access_rule: a block with ``keyword == "wlan access-rule"``. The
            block's own name (``args[0]``) becomes both the policy name and
            the implicit role every rule's source is scoped to.
    """
    role_name = (access_rule.get("args") or [""])[0]
    rules: list[dict[str, Any]] = []
    unmapped: list[str] = []
    position = 1
    for tokens in prop_all(access_rule, "rule"):
        built = _build_rule(role_name, tokens, position, unmapped)
        if built is None:
            continue
        rules.append(built)
        position += 1
    return CanonicalPolicy(name=role_name, association="ASSOCIATION_ROLE", rules=rules, unmapped_actions=unmapped)
