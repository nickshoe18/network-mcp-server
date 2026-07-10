"""GreenLake Authorization tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/authorization__groups.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``authorization``   tag: ``groups``   operations: 9
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_delete_workspaces_v1beta1_groups_group_id",
    description="DELETE /workspaces/v1beta1/groups/{groupId}\n\nremoveGroupV2\n\nDelete the workspace group",
    tags={"authorization", "greenlake", "greenlake_write_delete", "requires_confirmation"},
    annotations={
        "title": "Delete the workspace group",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_workspaces_v1beta1_groups_group_id(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake group ID")],
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}"
    return await greenlake_request(
        ctx,
        "DELETE",
        path,
    )


@tool(
    name="greenlake_delete_workspaces_v1beta1_groups_group_id_group_workspaces_group_workspace_id",
    description="DELETE /workspaces/v1beta1/groups/{groupId}/group-workspaces/{groupWorkspaceId}\n\ndeleteWorkspaceFromGroup\n\nRemove a workspace from the workspace group",
    tags={"authorization", "greenlake", "greenlake_write_delete", "requires_confirmation"},
    annotations={
        "title": "Remove a workspace from the workspace group",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_workspaces_v1beta1_groups_group_id_group_workspaces_group_workspace_id(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake unique group ID")],
    groupWorkspaceId: Annotated[
        str, Field(description="HPE GreenLake unique resource ID for this workspace belonging to the group")
    ],
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}/group-workspaces/{path_seg(groupWorkspaceId)}"
    return await greenlake_request(
        ctx,
        "DELETE",
        path,
    )


@tool(
    name="greenlake_get_workspaces_v1beta1_groups",
    description="GET /workspaces/v1beta1/groups\n\ngetGroupsV2\n\nList of Paginated workspace groups",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "List of Paginated workspace groups",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_workspaces_v1beta1_groups(
    ctx: Context,
    offset: Annotated[
        int | None, Field(default=None, description="The starting offset from which to begin retrieving items")
    ] = None,
    limit: Annotated[
        int | None,
        Field(
            default=None, description="Specifies the number of query results to be returned in a query response page"
        ),
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if offset is not None:
        query_params["offset"] = offset
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/workspaces/v1beta1/groups",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_workspaces_v1beta1_groups_group_id",
    description="GET /workspaces/v1beta1/groups/{groupId}\n\nfetchGroupV2\n\nGet the workspace group details",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "Get the workspace group details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_workspaces_v1beta1_groups_group_id(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake unique group ID")],
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_get_workspaces_v1beta1_groups_group_id_group_workspaces",
    description="GET /workspaces/v1beta1/groups/{groupId}/group-workspaces\n\nlistGroupWorkspaces\n\nList of paginated workspaces associated with the group ID",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "List of paginated workspaces associated with the group ID",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_workspaces_v1beta1_groups_group_id_group_workspaces(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake group ID")],
    limit: Annotated[
        int | None,
        Field(
            default=None, description="Specifies the number of query results to be returned in a query response page"
        ),
    ] = None,
    offset: Annotated[
        int | None, Field(default=None, description="The starting offset from which to begin retrieving items")
    ] = None,
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}/group-workspaces"
    query_params: dict[str, Any] = {}
    if limit is not None:
        query_params["limit"] = limit
    if offset is not None:
        query_params["offset"] = offset
    return await greenlake_request(
        ctx,
        "GET",
        path,
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_workspaces_v1beta1_groups_group_id_group_workspaces_group_workspace_id",
    description="GET /workspaces/v1beta1/groups/{groupId}/group-workspaces/{groupWorkspaceId}\n\ngetGroupWorkspace\n\nGet the workspace details",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "Get the workspace details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_workspaces_v1beta1_groups_group_id_group_workspaces_group_workspace_id(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake unique group ID")],
    groupWorkspaceId: Annotated[
        str, Field(description="HPE GreenLake unique resource ID for this workspace belonging to the group")
    ],
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}/group-workspaces/{path_seg(groupWorkspaceId)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_post_workspaces_v1beta1_groups",
    description="POST /workspaces/v1beta1/groups\n\ncreateNewGroupV2\n\nCreate a workspace group",
    tags={"authorization", "greenlake", "greenlake_write", "requires_confirmation"},
    annotations={
        "title": "Create a workspace group",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_workspaces_v1beta1_groups(
    ctx: Context,
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    return await greenlake_request(
        ctx,
        "POST",
        "/workspaces/v1beta1/groups",
        body=body,
    )


@tool(
    name="greenlake_post_workspaces_v1beta1_groups_group_id_group_workspaces",
    description="POST /workspaces/v1beta1/groups/{groupId}/group-workspaces\n\naddWorkspaceToGroup\n\nAdd a workspace to the group",
    tags={"authorization", "greenlake", "greenlake_write", "requires_confirmation"},
    annotations={
        "title": "Add a workspace to the group",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_workspaces_v1beta1_groups_group_id_group_workspaces(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake unique group ID")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}/group-workspaces"
    return await greenlake_request(
        ctx,
        "POST",
        path,
        body=body,
    )


@tool(
    name="greenlake_put_workspaces_v1beta1_groups_group_id",
    description="PUT /workspaces/v1beta1/groups/{groupId}\n\nputGroupV2\n\nUpdate workspace group details",
    tags={"authorization", "greenlake", "greenlake_write", "requires_confirmation"},
    annotations={
        "title": "Update workspace group details",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_put_workspaces_v1beta1_groups_group_id(
    ctx: Context,
    groupId: Annotated[str, Field(description="HPE GreenLake unique group ID")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    path = f"/workspaces/v1beta1/groups/{path_seg(groupId)}"
    return await greenlake_request(
        ctx,
        "PUT",
        path,
        body=body,
    )
