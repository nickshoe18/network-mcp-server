"""Juniper SRX platform module — direct NETCONF-over-SSH CLI access.

Fills a gap Security Director Cloud's API doesn't cover: firewall
security-policy/NAT/address-object configuration. Auth is the device's
normal SSH username/password (see ``config.py:SRXSecrets``); transport
is PyEZ (``junos-eznc``) over NETCONF. Read-only first pass -- device
facts and a ``show``-restricted CLI passthrough only. No config-changing
(commit) tools yet; when those are added they'll need ``commit
confirmed`` auto-rollback plus the universal confirmation gate
(``requires_confirmation``, see ``middleware/elicitation.py``) given how
easily a bad security-policy push can sever the very session making it.

NOT YET LIVE-VERIFIED against a real device -- see ``client.py`` module
docstring.
"""

import importlib

from fastmcp import FastMCP
from loguru import logger

from hpe_networking_mcp.config import ServerConfig

# Map of category (sub-module name under ``tools/``) -> list of tool names
# registered by that module. Mirrors every other platform's pattern.
TOOLS: dict[str, list[str]] = {
    "device": [
        "srx_get_facts",
        "srx_show_command",
    ],
}


def register_tools(mcp: FastMCP, config: ServerConfig) -> int:
    """Load SRX tool modules and register them with FastMCP.

    Always imports every category so the platform registry is fully
    populated; runtime write-gating is handled by the ``Visibility``
    transform (static mode) and ``is_tool_enabled`` (dynamic mode, via
    the meta-tools).

    Returns the count of individual underlying tools that registered.
    """
    from hpe_networking_mcp.platforms._common.meta_tools import build_meta_tools
    from hpe_networking_mcp.platforms.srx import _registry

    _registry.mcp = mcp

    loaded: list[str] = []
    for category, tool_names in TOOLS.items():
        try:
            importlib.import_module(f"hpe_networking_mcp.platforms.srx.tools.{category}")
            loaded.extend(tool_names)
            logger.debug("SRX: loaded module {}", category)
        except Exception as e:
            logger.warning("SRX: failed to load module {} -- {}", category, e)

    # Meta-tools are always registered (issue #302). In code mode they're
    # reachable via ``await call_tool("srx_list_tools", ...)`` from inside
    # ``execute()`` even though they're hidden from the top-level catalog.
    build_meta_tools("srx", mcp)
    logger.info(
        "SRX: {} underlying tools + 3 meta-tools registered ({} mode)",
        len(loaded),
        config.tool_mode,
    )

    return len(loaded)
