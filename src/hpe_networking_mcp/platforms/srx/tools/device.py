"""SRX device identity and read-only CLI tools.

First pass is deliberately narrow: device facts, plus a single
``show``-restricted CLI passthrough that covers full/hierarchy-filtered
config export (``show configuration [hierarchy]``) as well as ordinary
operational queries (``show security policies``, ``show route``, ...).
Junos's own CLI already does the hierarchy filtering, so there's no
separate NETCONF get-config filter path to get wrong without a live
device to verify it against.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.srx._registry import tool
from hpe_networking_mcp.platforms.srx.client import format_srx_error, get_srx_client
from hpe_networking_mcp.platforms.srx.tools import READ_ONLY


@tool(annotations=READ_ONLY)
async def srx_get_facts(ctx: Context) -> dict[str, Any] | str:
    """Get device facts for the configured SRX (hostname, model, Junos version, serial number, etc.)."""
    try:
        client = await get_srx_client()
        return await client.get_facts()
    except Exception as e:
        return f"Error fetching SRX facts: {format_srx_error(e)}"


@tool(annotations=READ_ONLY)
async def srx_show_command(
    ctx: Context,
    command: Annotated[
        str,
        Field(
            description=(
                "A read-only Junos 'show' command, e.g. 'show configuration', "
                "'show configuration security policies', 'show configuration security nat', "
                "'show configuration security address-book', 'show security policies', "
                "'show route', 'show interfaces terse'. Must start with 'show' -- "
                "this platform has no config-changing tools yet."
            )
        ),
    ],
) -> str:
    """Run a read-only 'show' command on the SRX and return its CLI text output."""
    try:
        client = await get_srx_client()
        return await client.show(command)
    except Exception as e:
        return f"Error running show command: {format_srx_error(e)}"
