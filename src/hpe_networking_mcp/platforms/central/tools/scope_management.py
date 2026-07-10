"""Aruba Central ``scope-management`` config-model tools.

Ported from the upstream ``nowireless4u/hpe-networking-mcp`` project
(``platforms/central/tools/scope_management.py``, itself emitted by their
``scripts/import_central_config_tools.py`` from a snapshot of
``vendor/central/config/``). Covers device-collection bulk operations —
a distinct config-model resource from the older ``device-groups`` API in
``configuration.py``. Wrappers delegate to ``_get_resource`` /
``_manage_resource`` / ``_operation_request`` in ``security_policy.py`` —
the same shared helpers used by the hand-curated Roles & Policy tools.
"""

# ruff: noqa: E501

from typing import Annotated

from fastmcp import Context
from pydantic import Field

from hpe_networking_mcp.platforms.central._registry import tool
from hpe_networking_mcp.platforms.central.tools import READ_ONLY
from hpe_networking_mcp.platforms.central.tools.security_policy import (
    _CONFIRMED_FIELD,
    _DEVICE_FUNCTION_FIELD,
    _SCOPE_ID_FIELD,
    WRITE_DELETE,
    _get_resource,
    _manage_resource,
    _operation_request,
)

# ----- device-collection-add-devices -----


@tool(annotations=WRITE_DELETE, tags={"central_write_delete"})
async def central_manage_device_collection_add_devices(
    ctx: Context,
    action_type: Annotated[str, Field(description="``'create'``, ``'update'``, or ``'delete'``.")],
    payload: Annotated[
        dict,
        Field(
            description=(
                "Payload for the singleton ``device-collection-add-devices`` object. "
                "Consult the Aruba Central config-model OpenAPI schema for the "
                "field set; use ``central_get_device_collections`` to "
                "inspect the current state. For ``delete``, ``payload`` is ignored."
            )
        ),
    ],
    scope_id: Annotated[str | None, _SCOPE_ID_FIELD] = None,
    device_function: Annotated[str | None, _DEVICE_FUNCTION_FIELD] = None,
    confirmed: Annotated[bool, _CONFIRMED_FIELD] = False,
) -> dict | str:
    """Create, update, or delete the singleton ``device-collection-add-devices`` configuration in Central.

    This API adds devices to an existing device collection. Returns a list of
    device-groups, based on the query parameters. Each device-group includes
    deviceCount, id, type, description, scopeId, scopeName.
    """
    return await _manage_resource(
        ctx,
        "device-collection-add-devices",
        "device-collection-add-devices",
        None,
        action_type,
        payload,
        scope_id,
        device_function,
        confirmed,
    )


# ----- device-collection-create-and-add-devices -----


@tool(annotations=WRITE_DELETE, tags={"central_write_delete"})
async def central_manage_device_collection_create_and_add_devices(
    ctx: Context,
    action_type: Annotated[str, Field(description="``'create'``, ``'update'``, or ``'delete'``.")],
    payload: Annotated[
        dict,
        Field(
            description=(
                "Payload for the singleton ``device-collection-create-and-add-devices`` object. "
                "Consult the Aruba Central config-model OpenAPI schema for the "
                "field set; use ``central_get_device_collections`` to "
                "inspect the current state. For ``delete``, ``payload`` is ignored."
            )
        ),
    ],
    scope_id: Annotated[str | None, _SCOPE_ID_FIELD] = None,
    device_function: Annotated[str | None, _DEVICE_FUNCTION_FIELD] = None,
    confirmed: Annotated[bool, _CONFIRMED_FIELD] = False,
) -> dict | str:
    """Create, update, or delete the singleton ``device-collection-create-and-add-devices`` configuration in Central.

    Creates a new device collection and adds devices to it in one call.
    """
    return await _manage_resource(
        ctx,
        "device-collection-create-and-add-devices",
        "device-collection-create-and-add-devices",
        None,
        action_type,
        payload,
        scope_id,
        device_function,
        confirmed,
    )


# ----- device-collection-remove-devices -----


@tool(annotations=WRITE_DELETE, tags={"central_write_delete"})
async def central_manage_device_collection_remove_devices(
    ctx: Context,
    action_type: Annotated[str, Field(description="``'create'``, ``'update'``, or ``'delete'``.")],
    payload: Annotated[
        dict,
        Field(
            description=(
                "Payload for the singleton ``device-collection-remove-devices`` object. "
                "Consult the Aruba Central config-model OpenAPI schema for the "
                "field set; use ``central_get_device_collections`` to "
                "inspect the current state. For ``delete``, ``payload`` is ignored."
            )
        ),
    ],
    scope_id: Annotated[str | None, _SCOPE_ID_FIELD] = None,
    device_function: Annotated[str | None, _DEVICE_FUNCTION_FIELD] = None,
    confirmed: Annotated[bool, _CONFIRMED_FIELD] = False,
) -> dict | str:
    """Create, update, or delete the singleton ``device-collection-remove-devices`` configuration in Central.

    Removes devices from an existing device collection.
    """
    return await _manage_resource(
        ctx,
        "device-collection-remove-devices",
        "device-collection-remove-devices",
        None,
        action_type,
        payload,
        scope_id,
        device_function,
        confirmed,
    )


# ----- device-collections -----


@tool(annotations=READ_ONLY)
async def central_get_device_collections(
    ctx: Context,
) -> dict | list | str:
    """Get the ``device-collections`` singleton configuration from Central.

    Returns a list of device-groups (collections), based on the query
    parameters. Each entry includes deviceCount, id, type, description,
    scopeId, scopeName. Distinct from the older ``device-groups`` API in
    ``configuration.py`` (``central_manage_device_group``).
    """
    return await _get_resource(ctx, "device-collections", None)


@tool(annotations=WRITE_DELETE, tags={"central_write_delete"})
async def central_manage_device_collections(
    ctx: Context,
    action_type: Annotated[str, Field(description="``'create'``, ``'update'``, or ``'delete'``.")],
    payload: Annotated[
        dict,
        Field(
            description=(
                "Payload for the singleton ``device-collections`` object. "
                "Consult the Aruba Central config-model OpenAPI schema for the "
                "field set; use ``central_get_device_collections`` to "
                "inspect the current state. For ``delete``, ``payload`` is ignored."
            )
        ),
    ],
    scope_id: Annotated[str | None, _SCOPE_ID_FIELD] = None,
    device_function: Annotated[str | None, _DEVICE_FUNCTION_FIELD] = None,
    confirmed: Annotated[bool, _CONFIRMED_FIELD] = False,
) -> dict | str:
    """Create, update, or delete the singleton ``device-collections`` configuration in Central."""
    return await _manage_resource(
        ctx,
        "device-collections",
        "device-collections",
        None,
        action_type,
        payload,
        scope_id,
        device_function,
        confirmed,
    )


# ----- operation: device-collections/bulk -----


@tool(annotations=WRITE_DELETE, tags={"central_write_delete"})
async def central_device_collections_bulk_delete(
    ctx: Context,
    payload: Annotated[
        dict,
        Field(
            description=(
                "Request body for the ``device-collections/bulk`` operation "
                "(e.g. ``{'items': [...]}`` selecting the collections to delete). "
                "Consult the Aruba Central config-model OpenAPI schema for the field set."
            )
        ),
    ],
    confirmed: Annotated[bool, _CONFIRMED_FIELD] = False,
) -> dict | str:
    """Bulk-delete device collections.

    Wraps ``DELETE network-config/v1alpha1/device-collections/bulk``.
    """
    api_path = "network-config/v1alpha1/device-collections/bulk"
    return await _operation_request(ctx, "DELETE", api_path, payload, confirmed, "device-collections/bulk")
