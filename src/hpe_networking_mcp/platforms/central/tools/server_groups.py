"""Aruba Central server group configuration tools.

Provides read and write access to Central's RADIUS/auth server groups.
Server groups are named references used in WLAN profiles and switch
AAA/port-access config for authentication and accounting servers.
"""

from typing import Annotated

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.central._registry import tool
from hpe_networking_mcp.platforms.central.tools import READ_ONLY
from hpe_networking_mcp.platforms.central.tools.security_policy import (
    WRITE_DELETE,
    _CONFIRMED_FIELD,
    _DEVICE_FUNCTION_FIELD,
    _SCOPE_ID_FIELD,
    _get_resource,
    _manage_resource,
)


@tool(annotations=READ_ONLY)
async def central_get_server_groups(
    ctx: Context,
    name: str | None = None,
) -> dict | list | str:
    """
    Get RADIUS/auth server group configurations from Aruba Central.

    Server groups define collections of RADIUS servers used by WLAN
    profiles for authentication and accounting. Use this to resolve
    a server group name (from a WLAN profile's auth-server-group field)
    to its actual server IP addresses and settings.

    Parameters:
        name: Specific server group name to retrieve. If omitted, returns all groups.

    Returns:
        Single server group dict if name specified, or list of all groups.
    """
    return await _get_resource(ctx, "server-groups", name)


@tool(annotations=WRITE_DELETE, tags={"central_write_delete"})
async def central_manage_auth_server_group(
    ctx: Context,
    name: Annotated[str, Field(description="Server group identifier (OpenAPI path param: ``name``).")],
    action_type: Annotated[str, Field(description="``'create'``, ``'update'``, or ``'delete'``.")],
    payload: Annotated[
        dict,
        Field(
            description=(
                "Payload for the server-group object. "
                "Consult the Aruba Central config-model OpenAPI schema for the "
                "field set; use ``central_get_server_groups`` to "
                "inspect an existing object for reference. "
                "For ``delete``, ``payload`` is ignored."
            )
        ),
    ],
    scope_id: Annotated[str | None, _SCOPE_ID_FIELD] = None,
    device_function: Annotated[str | None, _DEVICE_FUNCTION_FIELD] = None,
    confirmed: Annotated[bool, _CONFIRMED_FIELD] = False,
) -> dict | str:
    """Create, update, or delete a RADIUS/auth server-group configuration in Central.

    Server groups define named collections of RADIUS servers (e.g. for
    switch AAA dot1x/mac-auth or WLAN profiles). Use this to create a
    new group, add/remove member servers, or delete a group that's no
    longer needed.
    """
    return await _manage_resource(
        ctx,
        "server-groups",
        "auth-server-group",
        name,
        action_type,
        payload,
        scope_id,
        device_function,
        confirmed,
    )
