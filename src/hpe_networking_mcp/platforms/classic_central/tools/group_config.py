"""Group-level configuration read tools for Classic Central.

Non-template ("UI") groups don't carry per-device variables the way
template groups do (see ``tools/variables.py``) -- their group-wide
config (VLANs, WLAN SSIDs, RADIUS auth-servers, roles/access-rules,
uplink/WAN-failover) is exposed as a single CLI-style config export via
``GET /configuration/v1/ap_cli/{group_name}`` -- confirmed live against
this tenant's "Wayne Enterprises" and "default" groups. This is the
source data the ``classic_central`` translation reader parses into
canonical models (see ``translations/readers/classic_central/``).

Despite the "ap_cli" name this endpoint returns the group's *entire*
shared config, not just AP-specific settings -- confirmed by real
VLAN/uplink/wired-port-profile content appearing in the response
alongside WLAN config.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.classic_central._registry import tool
from hpe_networking_mcp.platforms.classic_central.client import format_http_error, get_classic_central_client
from hpe_networking_mcp.platforms.classic_central.tools import READ_ONLY


@tool(annotations=READ_ONLY)
async def classic_central_get_groups(ctx: Context) -> list[dict[str, Any]] | str:
    """List Classic Central groups, including each one's ``template_group`` flag.

    A group with ``template_group: false`` is a "UI"/non-template group --
    its config is read via ``classic_central_get_group_config``, not
    ``classic_central_get_variables`` (that's for template groups only).
    """
    try:
        client = await get_classic_central_client()
        payload = await client.get_json("/configuration/v1/groups", params={"limit": 100, "offset": 0})
        return payload.get("data", payload) if isinstance(payload, dict) else payload
    except Exception as e:
        return f"Error fetching groups: {format_http_error(e) if hasattr(e, 'response') else e}"


@tool(annotations=READ_ONLY)
async def classic_central_get_group_config(
    ctx: Context,
    group_name: Annotated[
        str, Field(description="The real group name, e.g. 'Wayne Enterprises' -- not a site name or numeric group id.")
    ],
) -> list[str] | str:
    """Get a non-template group's entire shared config as an array of CLI text lines.

    Covers VLANs, WLAN SSID profiles, RADIUS auth-servers, roles/access-rules,
    RF profiles, netdestinations, and the uplink/WAN-failover block in one call.
    Secrets are pre-masked by the API itself (e.g. ``wpa-passphrase ********``).
    """
    try:
        client = await get_classic_central_client()
        payload = await client.get_json(f"/configuration/v1/ap_cli/{group_name}")
        return payload
    except Exception as e:
        return f"Error fetching group config: {format_http_error(e) if hasattr(e, 'response') else e}"
