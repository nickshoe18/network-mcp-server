"""Security Director Cloud site-management tools.

Endpoints confirmed against the live OpenAPI spec (tag ``Site Management``,
``/api/v2/site(s)``) -- see client.py's module docstring.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.security_director._registry import tool
from hpe_networking_mcp.platforms.security_director.client import format_http_error, get_security_director_client
from hpe_networking_mcp.platforms.security_director.tools import READ_ONLY


@tool(annotations=READ_ONLY)
async def security_director_get_sites(
    ctx: Context,
    size: Annotated[str | None, Field(default=None, description="Max entries to fetch (API default 100).")] = None,
    from_: Annotated[
        str | None, Field(default=None, alias="from", description="Starting offset (API default 0).")
    ] = None,
) -> list[dict[str, Any]] | dict[str, Any] | str:
    """List SD-WAN/SASE sites configured in Security Director Cloud."""
    try:
        client = await get_security_director_client()
        params: dict[str, Any] = {}
        if size is not None:
            params["spec.size"] = size
        if from_ is not None:
            params["spec.from"] = from_
        payload = await client.get_json("/api/v2/sites", params=params)
        return payload.get("items", payload) if isinstance(payload, dict) else payload
    except Exception as e:
        return f"Error fetching sites: {format_http_error(e) if hasattr(e, 'response') else e}"


@tool(annotations=READ_ONLY)
async def security_director_get_site(
    ctx: Context,
    site_name: Annotated[str, Field(description="The site's name.")],
) -> dict[str, Any] | str:
    """Get details for a single site by name."""
    try:
        client = await get_security_director_client()
        return await client.get_json(f"/api/v2/site/{site_name}")
    except Exception as e:
        return f"Error fetching site: {format_http_error(e) if hasattr(e, 'response') else e}"
