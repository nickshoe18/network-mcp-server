"""Classic Aruba Central platform module.

Distinct from ``platforms/central`` (New Central) — Classic Central is an
older, separate API/product surface with its own OAuth2 refresh-token auth
flow and endpoint set. Devices not yet migrated to New Central (e.g.
template-managed switches) are only reachable through this platform.
"""

import importlib

from fastmcp import FastMCP
from loguru import logger

from hpe_networking_mcp.config import ServerConfig

# Map of category (sub-module name under ``tools/``) -> list of tool names
# registered by that module. Mirrors every other platform's pattern.
TOOLS: dict[str, list[str]] = {
    "devices": [
        "classic_central_get_devices",
        "classic_central_get_device_detail",
        "classic_central_get_sites",
    ],
    "variables": [
        "classic_central_get_variables",
        "classic_central_manage_variables",
    ],
}


def register_tools(mcp: FastMCP, config: ServerConfig) -> int:
    """Load Classic Central tool modules and register them with FastMCP.

    Always imports every category so the platform registry is fully
    populated; runtime write-gating is handled by the ``Visibility``
    transform (static mode) and ``is_tool_enabled`` (dynamic mode, via
    the meta-tools).

    Returns the count of individual underlying tools that registered.
    """
    from hpe_networking_mcp.platforms._common.meta_tools import build_meta_tools
    from hpe_networking_mcp.platforms.classic_central import _registry

    _registry.mcp = mcp

    loaded: list[str] = []
    for category, tool_names in TOOLS.items():
        try:
            importlib.import_module(f"hpe_networking_mcp.platforms.classic_central.tools.{category}")
            loaded.extend(tool_names)
            logger.debug("Classic Central: loaded module {}", category)
        except Exception as e:
            logger.warning("Classic Central: failed to load module {} -- {}", category, e)

    # Meta-tools are always registered (issue #302). In code mode they're
    # reachable via ``await call_tool("classic_central_list_tools", ...)`` from
    # inside ``execute()`` even though they're hidden from the top-level catalog.
    build_meta_tools("classic_central", mcp)
    logger.info(
        "Classic Central: {} underlying tools + 3 meta-tools registered ({} mode)",
        len(loaded),
        config.tool_mode,
    )

    return len(loaded)
