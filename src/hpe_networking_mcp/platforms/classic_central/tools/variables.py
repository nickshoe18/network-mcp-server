"""Template-variable read/write tools for Classic Central.

Classic Central's template-based switches (the deployment model used by
switches not yet migrated to New Central's UI-based config model) don't
take direct per-object config pushes the way New Central does — config is
driven by a Jinja2 template plus a per-device variables blob. Changing a
device's effective config on Classic Central usually means editing its
variables (e.g. VLAN lists, trunk ranges) and letting Central re-render
and push the template, not calling an object-level config API.
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from hpe_networking_mcp.middleware.elicitation import confirm_write
from hpe_networking_mcp.platforms.classic_central._registry import tool
from hpe_networking_mcp.platforms.classic_central.client import format_http_error, get_classic_central_client
from hpe_networking_mcp.platforms.classic_central.tools import READ_ONLY, WRITE


@tool(annotations=READ_ONLY)
async def classic_central_get_variables(ctx: Context, serial_number: str) -> dict[str, Any] | str:
    """Get the template variables blob for a single device.

    Args:
        serial_number: The device's serial number.
    """
    try:
        client = await get_classic_central_client()
        payload = await client.get_json(f"/configuration/v1/devices/{serial_number}/variables")
        return payload
    except Exception as e:
        return f"Error fetching variables: {format_http_error(e) if hasattr(e, 'response') else e}"


@tool(annotations=WRITE, tags={"classic_central_write"})
async def classic_central_manage_variables(
    ctx: Context,
    serial_number: str,
    variables: dict[str, Any],
    confirmed: bool = False,
) -> dict[str, Any] | str:
    """Replace a device's template variables (full replace, not a merge).

    Central re-renders and pushes the device's assigned template using
    these variables on save. Fetch the current blob with
    ``classic_central_get_variables`` first and edit it, rather than
    constructing one from scratch, or you'll drop any variable this call
    doesn't include.

    Args:
        serial_number: The device's serial number.
        variables: The full variables blob to write (not a partial patch).
        confirmed: Set true after user confirms. Skips re-prompting.
    """
    if not confirmed:
        decline = await confirm_write(
            ctx, f"Classic Central: replace template variables for device {serial_number}. Confirm?"
        )
        if decline:
            return decline

    try:
        client = await get_classic_central_client()
        response = await client.request(
            "PUT",
            f"/configuration/v1/devices/{serial_number}/variables",
            json_body={"variables": variables},
        )
        body: Any = response.json() if response.content else {"status": "accepted"}
        return {"serial_number": serial_number, "data": body}
    except Exception as e:
        return f"Error updating variables: {format_http_error(e) if hasattr(e, 'response') else e}"
