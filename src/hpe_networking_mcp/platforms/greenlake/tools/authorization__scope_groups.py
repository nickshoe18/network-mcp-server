"""GreenLake Authorization tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/authorization__scope_groups.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``authorization``   tag: ``scope_groups``   operations: 8
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_delete_authorization_v1beta1_scope_groups_id",
    description="DELETE /authorization/v1beta1/scope-groups/{id}\n\ndeleteScopeGroupV1beta1\n\nDelete a scope group instance by ID",
    tags={"authorization", "greenlake", "greenlake_write_delete", "requires_confirmation"},
    annotations={
        "title": "Delete a scope group instance by ID",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_authorization_v1beta1_scope_groups_id(
    ctx: Context,
    id: Annotated[str, Field(description="path parameter 'id'")],
) -> Any:
    path = f"/authorization/v1beta1/scope-groups/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "DELETE",
        path,
    )


@tool(
    name="greenlake_delete_authorization_v1beta1_scope_groups_id_scopes_bulk",
    description="DELETE /authorization/v1beta1/scope-groups/{id}/scopes/bulk\n\ndeleteScopeGroupScopesV1beta1\n\nDelete scopes from a scope group",
    tags={"authorization", "greenlake", "greenlake_write_delete", "requires_confirmation"},
    annotations={
        "title": "Delete scopes from a scope group",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_authorization_v1beta1_scope_groups_id_scopes_bulk(
    ctx: Context,
    id: Annotated[str, Field(description="path parameter 'id'")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    path = f"/authorization/v1beta1/scope-groups/{path_seg(id)}/scopes/bulk"
    return await greenlake_request(
        ctx,
        "DELETE",
        path,
        body=body,
    )


@tool(
    name="greenlake_get_authorization_v1beta1_scope_groups",
    description="GET /authorization/v1beta1/scope-groups\n\ngetScopeGroupsV1beta1\n\nRetrieve all scope groups",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "Retrieve all scope groups",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_authorization_v1beta1_scope_groups(
    ctx: Context,
    limit: Annotated[
        int | None,
        Field(
            default=None,
            description="Total number of results to be returned. If the parameter is not provided, it will return all records found.",
        ),
    ] = None,
    offset: Annotated[
        int | None, Field(default=None, description="Zero-based resource offset to start the response from")
    ] = None,
    filter: Annotated[
        str | None,
        Field(
            default=None,
            description="OData style filter for filtering scope groups. Supports `in` operator on `serviceMetadata/id`, `name` or `grn` attributes.",
        ),
    ] = None,
    sort: Annotated[
        str | None,
        Field(
            default=None,
            description="Sort results by a single attribute and allow setting a sorting direction as ascending (asc) or descending (desc). Sorting is valid only for `name` attribute. Default sorting direction if omitted is ascending.",
        ),
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if limit is not None:
        query_params["limit"] = limit
    if offset is not None:
        query_params["offset"] = offset
    if filter is not None:
        query_params["filter"] = filter
    if sort is not None:
        query_params["sort"] = sort
    return await greenlake_request(
        ctx,
        "GET",
        "/authorization/v1beta1/scope-groups",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_authorization_v1beta1_scope_groups_id",
    description="GET /authorization/v1beta1/scope-groups/{id}\n\ngetScopeGroupV1beta1\n\nRetrieve a scope group instance by ID",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "Retrieve a scope group instance by ID",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_authorization_v1beta1_scope_groups_id(
    ctx: Context,
    id: Annotated[str, Field(description="path parameter 'id'")],
) -> Any:
    path = f"/authorization/v1beta1/scope-groups/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_get_authorization_v1beta1_scope_groups_id_scopes",
    description="GET /authorization/v1beta1/scope-groups/{id}/scopes\n\ngetScopeGroupScopesV1beta1\n\nRetrieve the scope group scopes list",
    tags={"authorization", "greenlake"},
    annotations={
        "title": "Retrieve the scope group scopes list",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_authorization_v1beta1_scope_groups_id_scopes(
    ctx: Context,
    id: Annotated[str, Field(description="path parameter 'id'")],
    limit: Annotated[
        int | None,
        Field(
            default=None,
            description="Total number of results to be returned. If the parameter is not provided, it will return all records found.",
        ),
    ] = None,
    offset: Annotated[
        int | None, Field(default=None, description="Zero-based resource offset to start the response from")
    ] = None,
) -> Any:
    path = f"/authorization/v1beta1/scope-groups/{path_seg(id)}/scopes"
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
    name="greenlake_post_authorization_v1beta1_scope_groups",
    description="POST /authorization/v1beta1/scope-groups\n\ncreateScopeGroupV1beta1\n\nCreate a scope group",
    tags={"authorization", "greenlake", "greenlake_write", "requires_confirmation"},
    annotations={
        "title": "Create a scope group",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_authorization_v1beta1_scope_groups(
    ctx: Context,
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    return await greenlake_request(
        ctx,
        "POST",
        "/authorization/v1beta1/scope-groups",
        body=body,
    )


@tool(
    name="greenlake_post_authorization_v1beta1_scope_groups_id_scopes_batch",
    description="POST /authorization/v1beta1/scope-groups/{id}/scopes/batch\n\naddScopeGroupScopesV1beta1\n\nAdd scopes to a scope group",
    tags={"authorization", "greenlake", "greenlake_write", "requires_confirmation"},
    annotations={
        "title": "Add scopes to a scope group",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_authorization_v1beta1_scope_groups_id_scopes_batch(
    ctx: Context,
    id: Annotated[str, Field(description="path parameter 'id'")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    path = f"/authorization/v1beta1/scope-groups/{path_seg(id)}/scopes/batch"
    return await greenlake_request(
        ctx,
        "POST",
        path,
        body=body,
    )


@tool(
    name="greenlake_put_authorization_v1beta1_scope_groups_id",
    description="PUT /authorization/v1beta1/scope-groups/{id}\n\nupdateScopeGroupV1beta1\n\nUpdate a scope group instance by ID",
    tags={"authorization", "greenlake", "greenlake_write", "requires_confirmation"},
    annotations={
        "title": "Update a scope group instance by ID",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_put_authorization_v1beta1_scope_groups_id(
    ctx: Context,
    id: Annotated[str, Field(description="path parameter 'id'")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    path = f"/authorization/v1beta1/scope-groups/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "PUT",
        path,
        body=body,
    )
