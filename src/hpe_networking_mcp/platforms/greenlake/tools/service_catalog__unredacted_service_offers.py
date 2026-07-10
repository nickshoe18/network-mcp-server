"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__unredacted_service_offers.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``unredacted_service_offers``   operations: 2
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_service_catalog_v1alpha1_unredacted_service_offers",
    description="GET /service-catalog/v1alpha1/unredacted-service-offers\n\ngetUnredactedServiceOffers\n\nGet Unredacted Service Offers",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Unredacted Service Offers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_unredacted_service_offers(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of service offers.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
    category: Annotated[str | None, Field(default=None, description="Get service offer list by category")] = None,
    application_id: Annotated[
        str | None, Field(default=None, description="Get service offer list of an application")
    ] = None,
    status: Annotated[str | None, Field(default=None, description="Get service offer list for a status")] = None,
    is_service_manager: Annotated[bool | None, Field(default=None, description="Get list of service managers")] = None,
    slug: Annotated[str | None, Field(default=None, description="Get list of service offers by slug")] = None,
    static_launch_url: Annotated[
        str | None, Field(default=None, description="Get list of service offers by slug")
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    if category is not None:
        query_params["category"] = category
    if application_id is not None:
        query_params["application_id"] = application_id
    if status is not None:
        query_params["status"] = status
    if is_service_manager is not None:
        query_params["is_service_manager"] = is_service_manager
    if slug is not None:
        query_params["slug"] = slug
    if static_launch_url is not None:
        query_params["static_launch_url"] = static_launch_url
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1alpha1/unredacted-service-offers",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1alpha1_unredacted_service_offers_id",
    description="GET /service-catalog/v1alpha1/unredacted-service-offers/{id}\n\ngetUnredactedServiceOffer\n\nGet Unredacted Service Offer",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Unredacted Service Offer",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_unredacted_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
) -> Any:
    path = f"/service-catalog/v1alpha1/unredacted-service-offers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )
