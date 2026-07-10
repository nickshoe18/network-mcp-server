"""GreenLake Subscription Management tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/subscription_management__subscriptions_v1alpha1.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``subscription-management``   tag: ``subscriptions_v1alpha1``   operations: 1
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_subscriptions_v1alpha1_subscriptions",
    description="GET /subscriptions/v1alpha1/subscriptions\n\ngetSubscriptionsV1alpha1\n\nGet subscriptions of a workspace",
    tags={"greenlake", "subscription_management"},
    annotations={
        "title": "Get subscriptions of a workspace",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_subscriptions_v1alpha1_subscriptions(
    ctx: Context,
    filter: Annotated[
        str | None,
        Field(
            default=None,
            description="Filter expressions consisting of simple comparison operations joined by logical operators.",
        ),
    ] = None,
    sort: Annotated[
        str | None,
        Field(
            default=None,
            description="A comma separated list of sort expressions. A sort expression is a property name optionally followed by a direction indicator `asc` or `desc`. Default is ascending order.",
        ),
    ] = None,
    select: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="A comma separated list of select properties to return in the response. By default, all properties are returned.",
        ),
    ] = None,
    limit: Annotated[
        int | None,
        Field(default=None, description="Specifies the number of results to be returned. The default value is 2000."),
    ] = None,
    offset: Annotated[
        int | None,
        Field(
            default=None,
            description="Specifies the zero-based resource offset to start the response from. Default value is 0.",
        ),
    ] = None,
) -> Any:
    query_params: dict[str, Any] = {}
    if filter is not None:
        query_params["filter"] = filter
    if sort is not None:
        query_params["sort"] = sort
    if select is not None:
        query_params["select"] = select
    if limit is not None:
        query_params["limit"] = limit
    if offset is not None:
        query_params["offset"] = offset
    return await greenlake_request(
        ctx,
        "GET",
        "/subscriptions/v1alpha1/subscriptions",
        query_params=query_params or None,
    )
