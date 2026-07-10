"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__service_manager.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``service_manager``   operations: 4
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_service_catalog_v1_per_region_service_managers",
    description="GET /service-catalog/v1/per-region-service-managers\n\nper_region_service_managers_v1\n\nGet service managers by region",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get service managers by region",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1_per_region_service_managers(
    ctx: Context,
    offset: Annotated[
        int | None, Field(default=None, description="Zero-based resource offset to start the response from.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="The maximum number of records to return.")] = None,
    filter: Annotated[
        str | None,
        Field(
            default=None,
            description="Limit the resources operated on by an endpoint and return only the subset of resources that match the filter using an [OData V4](https://www.odata.org/documentation/) formatted filter string. Service manager by region can be filtered by `mspsupported` See examples of filtering options.",
        ),
    ] = None,
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
        "/service-catalog/v1/per-region-service-managers",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1_per_region_service_managers_id",
    description="GET /service-catalog/v1/per-region-service-managers/{id}\n\nservice_managers_for_a_region_v1\n\nGet service managers deployed in a specific region.",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get service managers deployed in a specific region.",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1_per_region_service_managers_id(
    ctx: Context,
    id: Annotated[str, Field(description="HPE GreenLake platform defined region code.")],
) -> Any:
    path = f"/service-catalog/v1/per-region-service-managers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_get_service_catalog_v1_service_managers",
    description="GET /service-catalog/v1/service-managers\n\nget_service_managers_v1\n\nGet service managers",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get service managers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1_service_managers(
    ctx: Context,
    offset: Annotated[int | None, Field(default=None, description="Specify pagination offset")] = None,
    limit: Annotated[int | None, Field(default=None, description="The maximum number of records to return.")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if offset is not None:
        query_params["offset"] = offset
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1/service-managers",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1_service_managers_id",
    description="GET /service-catalog/v1/service-managers/{id}\n\nget_service_manager_v1\n\nGet a specific service manager",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get a specific service manager",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1_service_managers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service manager ID")],
) -> Any:
    path = f"/service-catalog/v1/service-managers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )
