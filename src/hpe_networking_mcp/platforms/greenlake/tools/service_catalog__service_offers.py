"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__service_offers.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``service_offers``   operations: 11
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_delete_service_catalog_v1alpha1_service_offers_id",
    description="DELETE /service-catalog/v1alpha1/service-offers/{id}\n\ndeleteServiceOffer\n\nDelete Service Offer",
    tags={"greenlake", "greenlake_write_delete", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Delete Service Offer",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_service_catalog_v1alpha1_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
    If_Match: Annotated[int, Field(description="Generation version match")],
    force: Annotated[bool | None, Field(default=None, description="Specifies the force-delete action")] = None,
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}"
    query_params: dict[str, Any] = {}
    if force is not None:
        query_params["force"] = force
    header_params: dict[str, str] = {}
    if If_Match is not None:
        header_params["If-Match"] = str(If_Match)
    return await greenlake_request(
        ctx,
        "DELETE",
        path,
        query_params=query_params or None,
        header_params=header_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1alpha1_service_offers",
    description="GET /service-catalog/v1alpha1/service-offers\n\ngetServiceOffers\n\nGet Service Offers",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Service Offers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_service_offers(
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
        "/service-catalog/v1alpha1/service-offers",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1alpha1_service_offers_id",
    description="GET /service-catalog/v1alpha1/service-offers/{id}\n\ngetServiceOffer\n\nGet Service Offer",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Service Offer",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_service_offers",
    description="GET /service-catalog/v1beta1/service-offers\n\ngetServiceOffers\n\nGet service offers",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get service offers",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_service_offers(
    ctx: Context,
    next: Annotated[
        str | None,
        Field(default=None, description="Specifies the pagination cursor for the next page of service offers."),
    ] = None,
    limit: Annotated[
        int | None, Field(default=None, description="Specifies the number of results to be returned.")
    ] = None,
    filter: Annotated[
        str | None,
        Field(
            default=None,
            description="The `filter` query parameter is used to filter the set of resources returned in a `GET` request. The returned set of resources must match the criteria in the filter query parameter.<br><br> The value of the `filter` query parameter is a subset of [OData 4.0](https://www.odata.org/documentation/) filter expressions consisting of simple comparison operations joined by logical operators.<br><br>**Supported fields**: `category`, `serviceManagerId`, `status`, `isDefault`, `slug`, and `staticLaunchUrl`.<br>**Supported operand**: `eq`<br>**Supported operations**: `and`",
        ),
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if next is not None:
        query_params["next"] = next
    if limit is not None:
        query_params["limit"] = limit
    if filter is not None:
        query_params["filter"] = filter
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1beta1/service-offers",
        query_params=query_params or None,
    )


@tool(
    name="greenlake_get_service_catalog_v1beta1_service_offers_id",
    description="GET /service-catalog/v1beta1/service-offers/{id}\n\ngetServiceOffer\n\nGet a service offer",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get a service offer",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1beta1_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="The unique identifier of the service offer.")],
) -> Any:
    path = f"/service-catalog/v1beta1/service-offers/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_patch_service_catalog_v1alpha1_service_offers_id",
    description="PATCH /service-catalog/v1alpha1/service-offers/{id}\n\npatchServiceOffer\n\nPartially Update Service Offer",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Partially Update Service Offer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_patch_service_catalog_v1alpha1_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
    If_Match: Annotated[int, Field(description="Generation version match")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
    force: Annotated[
        bool | None,
        Field(default=None, description="Specifies the force-update action that ignores the dev_accounts list check"),
    ] = None,
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}"
    query_params: dict[str, Any] = {}
    if force is not None:
        query_params["force"] = force
    header_params: dict[str, str] = {}
    if If_Match is not None:
        header_params["If-Match"] = str(If_Match)
    return await greenlake_request(
        ctx,
        "PATCH",
        path,
        query_params=query_params or None,
        header_params=header_params or None,
        body=body,
    )


@tool(
    name="greenlake_post_service_catalog_v1alpha1_service_offers",
    description="POST /service-catalog/v1alpha1/service-offers\n\ncreateServiceOffer\n\nCreate Service Offer",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Create Service Offer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_service_catalog_v1alpha1_service_offers(
    ctx: Context,
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    return await greenlake_request(
        ctx,
        "POST",
        "/service-catalog/v1alpha1/service-offers",
        body=body,
    )


@tool(
    name="greenlake_post_service_catalog_v1alpha1_service_offers_id_hide",
    description="POST /service-catalog/v1alpha1/service-offers/{id}/hide\n\nhideServiceOffer\n\nHide Service Offer",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Hide Service Offer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_service_catalog_v1alpha1_service_offers_id_hide(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
    If_Match: Annotated[int, Field(description="Generation version match")],
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}/hide"
    header_params: dict[str, str] = {}
    if If_Match is not None:
        header_params["If-Match"] = str(If_Match)
    return await greenlake_request(
        ctx,
        "POST",
        path,
        header_params=header_params or None,
    )


@tool(
    name="greenlake_post_service_catalog_v1alpha1_service_offers_id_onboarded",
    description="POST /service-catalog/v1alpha1/service-offers/{id}/onboarded\n\nonboardServiceOffer\n\nMark Service Offer onboarding as complete",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Mark Service Offer onboarding as complete",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_service_catalog_v1alpha1_service_offers_id_onboarded(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
    If_Match: Annotated[int, Field(description="Generation version match")],
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}/onboarded"
    header_params: dict[str, str] = {}
    if If_Match is not None:
        header_params["If-Match"] = str(If_Match)
    return await greenlake_request(
        ctx,
        "POST",
        path,
        header_params=header_params or None,
    )


@tool(
    name="greenlake_post_service_catalog_v1alpha1_service_offers_id_publish",
    description="POST /service-catalog/v1alpha1/service-offers/{id}/publish\n\npublishServiceOffer\n\nPublish Service Offer",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Publish Service Offer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_service_catalog_v1alpha1_service_offers_id_publish(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
    If_Match: Annotated[int, Field(description="Generation version match")],
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}/publish"
    header_params: dict[str, str] = {}
    if If_Match is not None:
        header_params["If-Match"] = str(If_Match)
    return await greenlake_request(
        ctx,
        "POST",
        path,
        header_params=header_params or None,
    )


@tool(
    name="greenlake_put_service_catalog_v1alpha1_service_offers_id",
    description="PUT /service-catalog/v1alpha1/service-offers/{id}\n\nupdateServiceOffer\n\nUpdate Service Offer",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Update Service Offer",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_put_service_catalog_v1alpha1_service_offers_id(
    ctx: Context,
    id: Annotated[str, Field(description="Service offer ID")],
    If_Match: Annotated[int, Field(description="Generation version match")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
    force: Annotated[
        bool | None,
        Field(default=None, description="Specifies the force-update action that ignores the dev_accounts list check"),
    ] = None,
) -> Any:
    path = f"/service-catalog/v1alpha1/service-offers/{path_seg(id)}"
    query_params: dict[str, Any] = {}
    if force is not None:
        query_params["force"] = force
    header_params: dict[str, str] = {}
    if If_Match is not None:
        header_params["If-Match"] = str(If_Match)
    return await greenlake_request(
        ctx,
        "PUT",
        path,
        query_params=query_params or None,
        header_params=header_params or None,
        body=body,
    )
