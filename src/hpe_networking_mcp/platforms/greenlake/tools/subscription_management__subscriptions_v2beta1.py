"""GreenLake Subscription Management tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/subscription_management__subscriptions_v2beta1.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``subscription-management``   tag: ``subscriptions_v2beta1``   operations: 1
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_delete_subscriptions_v2beta1_subscriptions_bulk",
    description="DELETE /subscriptions/v2beta1/subscriptions/bulk\n\ndeleteSubscriptionsBulkV2Beta1\n\nUnclaim subscriptions in bulk",
    tags={"greenlake", "greenlake_write_delete", "requires_confirmation", "subscription_management"},
    annotations={
        "title": "Unclaim subscriptions in bulk",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_delete_subscriptions_v2beta1_subscriptions_bulk(
    ctx: Context,
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    return await greenlake_request(
        ctx,
        "DELETE",
        "/subscriptions/v2beta1/subscriptions/bulk",
        body=body,
    )
