"""GreenLake Subscription Management tools -- ported from upstream nowireless4u/hpe-networking-mcp.

Ported from ``platforms/greenlake/tools/subscription_management__auto_subscriptions_settings_v1alpha1.py`` in the upstream repo (generated
there from a vendored OpenAPI spec). Upstream's generator, ``Capability``
classification enum, and ``AsyncTokenManager`` auth were NOT ported -- this
file uses local's inline dict-annotation style and the ``greenlake_request()``
shim added to ``client.py`` for the actual HTTP transport.

Upstream service: ``subscription-management``   tag: ``auto_subscriptions_settings_v1alpha1``   operations: 3
"""

from __future__ import annotations

from typing import Annotated, Any

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms._common.url import path_seg
from hpe_networking_mcp.platforms.greenlake._registry import tool
from hpe_networking_mcp.platforms.greenlake.client import greenlake_request


@tool(
    name="greenlake_get_subscriptions_v1alpha1_auto_subscription_settings",
    description="GET /subscriptions/v1alpha1/auto-subscription-settings\n\ngetAutoSubscriptionsV1alpha1\n\nGet all configured auto-subscriptions settings",
    tags={"greenlake", "subscription_management"},
    annotations={
        "title": "Get all configured auto-subscriptions settings",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_subscriptions_v1alpha1_auto_subscription_settings(
    ctx: Context,
) -> Any:
    return await greenlake_request(
        ctx,
        "GET",
        "/subscriptions/v1alpha1/auto-subscription-settings",
    )


@tool(
    name="greenlake_get_subscriptions_v1alpha1_auto_subscription_settings_id",
    description="GET /subscriptions/v1alpha1/auto-subscription-settings/{id}\n\ngetAutoSubscriptionByIdV1alpha1\n\nGet configured auto-subscriptions settings per workspace",
    tags={"greenlake", "subscription_management"},
    annotations={
        "title": "Get configured auto-subscriptions settings per workspace",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    },
)
async def greenlake_get_subscriptions_v1alpha1_auto_subscription_settings_id(
    ctx: Context,
    id: Annotated[str, Field(description="The unique identifier of the workspace.")],
) -> Any:
    path = f"/subscriptions/v1alpha1/auto-subscription-settings/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "GET",
        path,
    )


@tool(
    name="greenlake_patch_subscriptions_v1alpha1_auto_subscription_settings_id",
    description="PATCH /subscriptions/v1alpha1/auto-subscription-settings/{id}\n\nupdateAutoSubscriptionsV1alpha1\n\nUpdate the configured auto-subscriptions settings of a workspace",
    tags={"greenlake", "greenlake_write", "requires_confirmation", "subscription_management"},
    annotations={
        "title": "Update the configured auto-subscriptions settings of a workspace",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True,
    },
)
async def greenlake_patch_subscriptions_v1alpha1_auto_subscription_settings_id(
    ctx: Context,
    id: Annotated[str, Field(description="The unique identifier of the auto subscription settings.")],
    body: Annotated[dict[str, Any], Field(description="Request body (required)")],
) -> Any:
    path = f"/subscriptions/v1alpha1/auto-subscription-settings/{path_seg(id)}"
    return await greenlake_request(
        ctx,
        "PATCH",
        path,
        body=body,
    )
