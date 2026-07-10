"""Juniper Security Director Cloud (SD Cloud) platform module.

SD-WAN/SASE site-and-device orchestration for SRX/vSRX fleets. Single
static API-key auth (see client.py). Initial tool set (devices, sites)
covers the two most broadly useful read paths confirmed against the real
published OpenAPI spec; Device Groups, Templates, and Tunnels are
additional confirmed-available domains not yet wrapped as tools. This
spec does NOT cover firewall security-policy/NAT/address-object CRUD --
that may live under a separate, not-yet-located API surface.
"""

import importlib

from fastmcp import FastMCP
from loguru import logger

from hpe_networking_mcp.config import ServerConfig

# Map of category (sub-module name under ``tools/``) -> list of tool names
# registered by that module. Mirrors every other platform's pattern.
TOOLS: dict[str, list[str]] = {
    "devices": [
        "security_director_get_devices",
        "security_director_get_device",
    ],
    "sites": [
        "security_director_get_sites",
        "security_director_get_site",
    ],
}


def register_tools(mcp: FastMCP, config: ServerConfig) -> int:
    """Load Security Director tool modules and register them with FastMCP.

    Always imports every category so the platform registry is fully
    populated; runtime write-gating is handled by the ``Visibility``
    transform (static mode) and ``is_tool_enabled`` (dynamic mode, via
    the meta-tools).

    Returns the count of individual underlying tools that registered.
    """
    from hpe_networking_mcp.platforms._common.meta_tools import build_meta_tools
    from hpe_networking_mcp.platforms.security_director import _registry

    _registry.mcp = mcp

    loaded: list[str] = []
    for category, tool_names in TOOLS.items():
        try:
            importlib.import_module(f"hpe_networking_mcp.platforms.security_director.tools.{category}")
            loaded.extend(tool_names)
            logger.debug("Security Director: loaded module {}", category)
        except Exception as e:
            logger.warning("Security Director: failed to load module {} -- {}", category, e)

    # Meta-tools are always registered (issue #302). In code mode they're
    # reachable via ``await call_tool("security_director_list_tools", ...)``
    # from inside ``execute()`` even though they're hidden from the top-level
    # catalog.
    build_meta_tools("security_director", mcp)
    logger.info(
        "Security Director: {} underlying tools + 3 meta-tools registered ({} mode)",
        len(loaded),
        config.tool_mode,
    )

    return len(loaded)
