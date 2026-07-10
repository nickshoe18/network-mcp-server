"""GreenLake Reporting tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/reporting__async_operations.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``reporting``   tag: ``async_operations``   operations: 1
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_reporting_v1_async_operations_id",
    description="GET /reporting/v1/async-operations/{id}\n\nAsynchronous operation details",
    tags={"greenlake", "reporting"},
    annotations={
        "title": "Asynchronous operation details",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_reporting_v1_async_operations_id(
    ctx: Context,
    id: Annotated[str, Field(description="The unique identifier returned by an asynchronous API call.")],
) -> Any:
    path = f"/reporting/v1/async-operations/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )
