"""Device inventory and monitoring read tools for Classic Central.

Paths live under ``/monitoring/v1/*`` and ``/central/v2/*`` -- confirmed
live against this tenant's API Gateway app (registered under the "nms"
scope), not guessed. The ``/platform/device_inventory/v1/devices`` path
returned a 500 for this app registration -- monitoring endpoints are
what it's actually scoped for.
"""

from __future__ import annotations

from typing import Any, Literal

from fastmcp import Context

from hpe_networking_mcp.platforms.classic_central._registry import tool
from hpe_networking_mcp.platforms.classic_central.client import format_http_error, get_classic_central_client
from hpe_networking_mcp.platforms.classic_central.tools import READ_ONLY


@tool(annotations=READ_ONLY)
async def classic_central_get_devices(
    ctx: Context,
    device_type: Literal["aps", "switches", "gateways", "controllers"],
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, Any]] | dict[str, Any] | str:
    """List devices of one type from Classic Central's monitoring API.

    Args:
        device_type: The device category to list.
        limit: Max records to return (Central caps this per-page; default 100).
        offset: Pagination offset.
    """
    try:
        client = await get_classic_central_client()
        # "aps" is v2 -- confirmed live (v1 404s). Every other device_type is v1.
        api_version = "v2" if device_type == "aps" else "v1"
        payload = await client.get_json(
            f"/monitoring/{api_version}/{device_type}", params={"limit": limit, "offset": offset}
        )
        return payload.get(device_type, payload) if isinstance(payload, dict) else payload
    except Exception as e:
        return f"Error fetching devices: {format_http_error(e) if hasattr(e, 'response') else e}"


@tool(annotations=READ_ONLY)
async def classic_central_get_device_detail(
    ctx: Context,
    serial_number: str,
    device_type: Literal["aps", "switches", "gateways", "controllers"],
) -> dict[str, Any] | str:
    """Get monitoring detail for a single device by serial number.

    Args:
        serial_number: The device's serial number.
        device_type: The Central monitoring category the device belongs to.
    """
    try:
        client = await get_classic_central_client()
        payload = await client.get_json(f"/monitoring/v1/{device_type}/{serial_number}")
        return payload
    except Exception as e:
        return f"Error fetching device detail: {format_http_error(e) if hasattr(e, 'response') else e}"


@tool(annotations=READ_ONLY)
async def classic_central_get_sites(ctx: Context, limit: int = 100, offset: int = 0) -> list[dict[str, Any]] | str:
    """List sites configured in Classic Central."""
    try:
        client = await get_classic_central_client()
        payload = await client.get_json("/central/v2/sites", params={"limit": limit, "offset": offset})
        return payload.get("sites", payload) if isinstance(payload, dict) else payload
    except Exception as e:
        return f"Error fetching sites: {format_http_error(e) if hasattr(e, 'response') else e}"
