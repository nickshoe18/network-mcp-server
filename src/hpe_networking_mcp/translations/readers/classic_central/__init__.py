"""Classic Central → canonical readers.

Source data is a whole-group CLI config dump (see
``platforms/classic_central/tools/group_config.py``), parsed generically
into blocks by ``_cli_parser.py``, then mapped per-kind into the same
canonical models the AOS8→Central engine already uses. Only the reader
side is new — every canonical model and every Central writer is fully
reused as-is.
"""

from __future__ import annotations

from hpe_networking_mcp.translations.readers.classic_central._cli_parser import (
    CliBlock,
    blocks_by_keyword,
    has_flag,
    parse_cli_blocks,
    prop,
    prop_all,
    prop_str,
)
from hpe_networking_mcp.translations.readers.classic_central.ap_uplink import classic_central_read_ap_uplink
from hpe_networking_mcp.translations.readers.classic_central.policy import classic_central_read_policy
from hpe_networking_mcp.translations.readers.classic_central.role import classic_central_read_skeletal_role
from hpe_networking_mcp.translations.readers.classic_central.vlan import classic_central_read_named_vlan
from hpe_networking_mcp.translations.readers.classic_central.wlan import classic_central_read_wlan

__all__ = [
    "CliBlock",
    "blocks_by_keyword",
    "classic_central_read_ap_uplink",
    "classic_central_read_named_vlan",
    "classic_central_read_policy",
    "classic_central_read_skeletal_role",
    "classic_central_read_wlan",
    "has_flag",
    "parse_cli_blocks",
    "prop",
    "prop_all",
    "prop_str",
]
