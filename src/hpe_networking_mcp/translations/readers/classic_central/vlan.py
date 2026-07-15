"""Classic Central → canonical named-VLAN reader.

Instant/IAP CLI always names its VLANs (``vlan <name> <id>``) -- there's no
bare-numeric-only construct distinct from AOS 8's ``vlan_id`` kind, so only
``named_vlan`` is wired for this source platform. Group-level VLANs only --
per-port manual assignments are explicitly out of scope (see project
memory: superseded by the colorless-ports project, not migrated as-is).
"""

from __future__ import annotations

from hpe_networking_mcp.translations.canonical.vlan import CanonicalNamedVlan
from hpe_networking_mcp.translations.readers.classic_central._cli_parser import CliBlock


def classic_central_read_named_vlan(block: CliBlock, *, alias_name: str | None = None) -> CanonicalNamedVlan:
    """Build a ``CanonicalNamedVlan`` from one ``vlan <name> <id>`` block.

    Args:
        block: a block with ``keyword == "vlan"`` from ``parse_cli_blocks``.
        alias_name: operator override for the alias name; defaults to the
            lower-case of the VLAN name (matches the AOS 8 reader's convention).
    """
    args = block.get("args") or []
    name = args[0] if len(args) > 0 else ""
    vlan_id = args[1] if len(args) > 1 else ""
    return CanonicalNamedVlan(
        vlan_name=name,
        alias_name=alias_name or name.lower(),
        vlan_ids=[vlan_id] if vlan_id else [],
    )
