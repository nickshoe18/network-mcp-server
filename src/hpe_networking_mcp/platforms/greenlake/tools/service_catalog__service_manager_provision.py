"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__service_manager_provision.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``service_manager_provision``   operations: 4
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_delete_service_catalog_v1_service_manager_provisions_id",
    description="DELETE /service-catalog/v1/service-manager-provisions/{id}\n\ndelete_service_manager_provision_v1\n\nDelete a service manager provision entry",
    tags={"greenlake", "greenlake_write_delete", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Delete a service manager provision entry",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_service_catalog_v1_service_manager_provisions_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service manager provision ID")],
) -> Any:
    path = f"/service-catalog/v1/service-manager-provisions/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "DELETE",
        path,
    )


@tool(
    name="greenlake_get_service_catalog_v1_service_manager_provisions",
    description="GET /service-catalog/v1/service-manager-provisions\n\nget_service_manager_provisions_v1\n\nGet service manager provisions",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get service manager provisions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1_service_manager_provisions(
    ctx: Context,
    offset: Annotated[
        int | None, Field(default=None, description="Zero-based resource offset to start the response from.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="The maximum number of records to return.")] = None,
    filter: Annotated[str | None, Field(default=None, description="query parameter 'filter'")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if offset is not None:
        query_params["offset"] = offset
    if limit is not None:
        query_params["limit"] = limit
    if filter is not None:
        query_params["filter"] = filter
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1/service-manager-provisions",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1_service_manager_provisions_id",
    description="GET /service-catalog/v1/service-manager-provisions/{id}\n\nget_service_manager_provision_v1\n\nGet a specific service manager provision entry",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get a specific service manager provision entry",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1_service_manager_provisions_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service manager provision ID")],
) -> Any:
    path = f"/service-catalog/v1/service-manager-provisions/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_post_service_catalog_v1_service_manager_provisions",
    description="POST /service-catalog/v1/service-manager-provisions\n\ncreate_service_manager_provision\n\nProvision a service manager in a given region",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Provision a service manager in a given region",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_service_catalog_v1_service_manager_provisions(
    ctx: Context,
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    return await greenlake_request(
        ctx,
        "POST",
        "/service-catalog/v1/service-manager-provisions",
        body=body,
    )
