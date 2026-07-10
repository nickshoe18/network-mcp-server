"""GreenLake Service Catalog tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/service_catalog__service_status.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``service-catalog``   tag: ``service_status``   operations: 1
"""

from __future__ import annotations

from typing import Any

from fastmcp import Context

from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_service_catalog_v1alpha1_health_service_registry",
    description="GET /service-catalog/v1alpha1/health/service-registry\n\ngetServiceRegistryHealth\n\nGet Status of service",
    tags={"greenlake", "service_catalog"},
    annotations={
        "title": "Get Status of service",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_service_catalog_v1alpha1_health_service_registry(
    ctx: Context,
) -> Any:
    return await greenlake_request(
        ctx,
        "GET",
        "/service-catalog/v1alpha1/health/service-registry",
    )
