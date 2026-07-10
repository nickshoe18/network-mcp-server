"""Security Director Cloud device inventory tools.

Endpoints confirmed against the live OpenAPI spec (tag ``Devices``,
``/api/v1/devices``) -- see client.py's module docstring.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.security_director._registry import tool
from hpe_networking_mcp.platforms.security_director.client import format_http_error, get_security_director_client
from hpe_networking_mcp.platforms.security_director.tools import READ_ONLY


@tool(annotations=READ_ONLY)
async def security_director_get_devices(
    ctx: Context,
    from_: Annotated[int, Field(default=0, alias="from", description="Zero-based pagination offset.")] = 0,
    size: Annotated[int, Field(default=50, description="Max results to return (API default 2000 if omitted).")] = 50,
    sortby: Annotated[str | None, Field(default=None, description="Field to sort by, e.g. 'name(ascending)'.")] = None,
    filters: Annotated[
        str | None,
        Field(
            default=None,
            description="Filter expression, e.g. '((name contains sometext) and (uuid eq dummy-id))'.",
        ),
    ] = None,
) -> list[dict[str, Any]] | dict[str, Any] | str:
    """List devices (SRX/vSRX firewalls) managed by Security Director Cloud."""
    try:
        client = await get_security_director_client()
        params: dict[str, Any] = {"from": from_, "size": size}
        if sortby is not None:
            params["sortby"] = sortby
        if filters is not None:
            params["filters"] = filters
        payload = await client.get_json("/api/v1/devices", params=params)
        return payload.get("items", payload) if isinstance(payload, dict) else payload
    except Exception as e:
        return f"Error fetching devices: {format_http_error(e) if hasattr(e, 'response') else e}"


@tool(annotations=READ_ONLY)
async def security_director_get_device(
    ctx: Context,
    device_uuid: Annotated[str, Field(description="The device's UUID.")],
) -> dict[str, Any] | str:
    """Get details for a single device by UUID."""
    try:
        client = await get_security_director_client()
        return await client.get_json(f"/api/v1/devices/{device_uuid}")
    except Exception as e:
        return f"Error fetching device: {format_http_error(e) if hasattr(e, 'response') else e}"
