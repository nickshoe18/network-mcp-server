"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__service_offers_migrate.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``service_offers_migrate``   operations: 1
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_post_service_catalog_v1alpha1_service_offers_migrate",
    description="POST /service-catalog/v1alpha1/service-offers/migrate\n\nmigrateServiceOffer\n\nMigrate applications to service offers",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "service_catalog"},
    annotations={
        "title": "Migrate applications to service offers",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_post_service_catalog_v1alpha1_service_offers_migrate(
    ctx: Context,
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    return await greenlake_request(
        ctx,
        "POST",
        "/service-catalog/v1alpha1/service-offers/migrate",
        body=body,
    )
