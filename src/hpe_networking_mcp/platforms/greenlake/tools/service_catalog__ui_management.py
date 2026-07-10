"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__ui_management.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``ui_management``   operations: 10
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_service_catalog_v1alpha1_detailed_service_offers_id",
    description="GET /service-catalog/v1alpha1/detailed-service-offers/{id}\n\ngetDetailedServiceOffer\n\nGet Service Offer Details",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Service Offer Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_detailed_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service Offer ID or SLUG")],
) -> Any:
    path = f"/service-catalog/v1alpha1/detailed-service-offers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_get_service_catalog_v1alpha1_featured_services",
    description="GET /service-catalog/v1alpha1/featured-services\n\ngetFeaturedServices\n\nGet Featured Service Offers",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Featured Service Offers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_featured_services(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of featured services.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1alpha1/featured-services",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1alpha1_my_services",
    description="GET /service-catalog/v1alpha1/my-services\n\ngetMyServices\n\nGet My Services",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get My Services",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_my_services(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of my services.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
    include_omnipresent: Annotated[
        bool | None,
        Field(default=None, description="Specifies whether to include omnipresent service offers in response"),
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    if include_omnipresent is not None:
        query_params["include_omnipresent"] = include_omnipresent
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1alpha1/my-services",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1alpha1_service_catalog",
    description="GET /service-catalog/v1alpha1/service-catalog\n\ngetServiceCatalog\n\nGet Service Offers for Catalog",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Service Offers for Catalog",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_service_catalog(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of service catalog.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1alpha1/service-catalog",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_detailed_service_offers_id",
    description="GET /service-catalog/v1beta1/detailed-service-offers/{id}\n\ngetDetailedServiceOffer\n\nGet Service Offer Details",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Service Offer Details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_detailed_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service Offer ID")],
) -> Any:
    path = f"/service-catalog/v1beta1/detailed-service-offers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_featured_services",
    description="GET /service-catalog/v1beta1/featured-services\n\ngetFeaturedServices\n\nGet Featured Service Offers",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Featured Service Offers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_featured_services(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the category for the next page of featured services.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1beta1/featured-services",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_my_services",
    description="GET /service-catalog/v1beta1/my-services\n\ngetMyServices\n\nGet My Services",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get My Services",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_my_services(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of my services.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
    include_omnipresent: Annotated[
        bool | None,
        Field(default=None, description="Specifies whether to include omnipresent service offers in response"),
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    if include_omnipresent is not None:
        query_params["include-omnipresent"] = include_omnipresent
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1beta1/my-services",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_recent_services",
    description="GET /service-catalog/v1beta1/recent-services\n\ngetRecentServices\n\nGet Recent Services",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Recent Services",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_recent_services(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of recent services.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1beta1/recent-services",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_service_catalog",
    description="GET /service-catalog/v1beta1/service-catalog\n\ngetServiceCatalog\n\nGet Service Offers for Catalog",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Service Offers for Catalog",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_service_catalog(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the category for the next page of service catalog.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1beta1/service-catalog",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta2_recent_services",
    description="GET /service-catalog/v1beta2/recent-services\n\ngetRecentServicesV2\n\nGet Recent Services",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Recent Services",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta2_recent_services(
    ctx: Context,
    next: Annotated[
        str | None, Field(default=None, description="Specifies the start-id for the next page of recent services.")
    ] = None,
    limit: Annotated[int | None, Field(default=None, description="Number of entries per page")] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1beta2/recent-services",
        query_params=query_params or None,
    )
