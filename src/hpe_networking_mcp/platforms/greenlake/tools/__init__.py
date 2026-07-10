"""GreenLake tools package.

Imports the tool modules so their ``@tool(...)`` decorators fire at module
load. Also exposes a ``TOOLS`` dict mapping category -> tool names so the
platform ``register_tools`` entry point can iterate over them and
``test_greenlake_dynamic_mode.py`` can assert the registry is fully
populated after import.

The five original hand-written modules (``audit_logs``, ``devices``,
``subscriptions``, ``users``, ``workspaces``) predate the upstream port and
keep their short category names. Everything else was ported from upstream
``nowireless4u/hpe-networking-mcp`` -- those modules follow upstream's
file-per-resource naming (``<domain>__<resource>``), and the dict key here
matches the module's short name exactly (the same rule
``_derive_category()`` in ``_registry.py`` uses to classify a tool at
runtime), grouped into 8 domains: device_management, subscription_management,
tags, location_management, event, authorization, service_catalog, reporting.
"""

from __future__ import annotations

# Categories are the short module names under ``platforms/greenlake/tools/``.
# Tool names match the ``name=...`` kwarg on each ``@tool(...)`` decorator.
TOOLS: dict[str, list[str]] = {
    "audit_logs": [
        "greenlake_get_audit_logs",
        "greenlake_get_audit_log_details",
    ],
    "devices": [
        "greenlake_get_devices",
        "greenlake_get_device_by_id",
    ],
    "subscriptions": [
        "greenlake_get_subscriptions",
        "greenlake_get_subscription_details",
    ],
    "users": [
        "greenlake_get_users",
        "greenlake_get_user_details",
    ],
    "workspaces": [
        "greenlake_get_workspace",
        "greenlake_get_workspace_details",
    ],
    # -- device_management -----------------------------------------------
    "device_management__devices_v1": [
        "greenlake_get_devices_v1_async_operations_id",
        "greenlake_get_devices_v1_devices",
        "greenlake_get_devices_v1_devices_id",
        "greenlake_patch_devices_v1_devices",
        "greenlake_post_devices_v1_devices",
    ],
    "device_management__devices_v1beta1": [
        "greenlake_get_devices_v1beta1_async_operations_id",
        "greenlake_get_devices_v1beta1_devices",
        "greenlake_get_devices_v1beta1_devices_id",
        "greenlake_patch_devices_v1beta1_devices",
        "greenlake_post_devices_v1beta1_devices",
    ],
    "device_management__devices_v2beta1": [
        "greenlake_get_devices_v2beta1_devices",
        "greenlake_get_devices_v2beta1_devices_group",
        "greenlake_get_devices_v2beta1_devices_id",
        "greenlake_patch_devices_v2beta1_devices",
        "greenlake_post_devices_v2beta1_devices",
    ],
    # -- subscription_management -------------------------------------------
    "subscription_management__subscriptions_v1": [
        "greenlake_get_subscriptions_v1_async_operations_id",
        "greenlake_get_subscriptions_v1_subscriptions",
        "greenlake_get_subscriptions_v1_subscriptions_id",
        "greenlake_patch_subscriptions_v1_subscriptions",
        "greenlake_post_subscriptions_v1_subscriptions",
    ],
    "subscription_management__subscriptions_v1alpha1": [
        "greenlake_get_subscriptions_v1alpha1_subscriptions",
    ],
    "subscription_management__subscriptions_v1beta1": [
        "greenlake_get_subscriptions_v1beta1_async_operations_id",
        "greenlake_get_subscriptions_v1beta1_subscriptions",
        "greenlake_get_subscriptions_v1beta1_subscriptions_id",
        "greenlake_patch_subscriptions_v1beta1_subscriptions",
        "greenlake_post_subscriptions_v1beta1_subscriptions",
    ],
    "subscription_management__subscriptions_v2beta1": [
        "greenlake_delete_subscriptions_v2beta1_subscriptions_bulk",
    ],
    "subscription_management__auto_subscriptions_settings_v1": [
        "greenlake_get_subscriptions_v1_auto_subscription_settings",
        "greenlake_get_subscriptions_v1_auto_subscription_settings_id",
        "greenlake_patch_subscriptions_v1_auto_subscription_settings_id",
    ],
    "subscription_management__auto_subscriptions_settings_v1alpha1": [
        "greenlake_get_subscriptions_v1alpha1_auto_subscription_settings",
        "greenlake_get_subscriptions_v1alpha1_auto_subscription_settings_id",
        "greenlake_patch_subscriptions_v1alpha1_auto_subscription_settings_id",
    ],
    # -- tags ---------------------------------------------------------------
    "tags__tags_v1": [
        "greenlake_get_tags_v1_tag_resources",
        "greenlake_get_tags_v1_tags",
    ],
    "tags__tags_v1beta1": [
        "greenlake_get_tags_v1beta1_tag_resources",
        "greenlake_get_tags_v1beta1_tags",
    ],
    # -- location_management -------------------------------------------------
    "location_management__locations": [
        "greenlake_delete_locations_v1_locations_id",
        "greenlake_get_locations_v1_locations",
        "greenlake_get_locations_v1_locations_address_revgeocode",
        "greenlake_get_locations_v1_locations_async_operation_id",
        "greenlake_get_locations_v1_locations_id",
        "greenlake_get_locations_v1_locations_status",
        "greenlake_get_locations_v1_locations_tags",
        "greenlake_get_locations_v1_locations_tags_id",
        "greenlake_patch_locations_v1_locations_id",
        "greenlake_patch_locations_v1_locations_tags",
        "greenlake_patch_locations_v1_locations_update_id",
        "greenlake_post_locations_v1_locations",
        "greenlake_post_locations_v1_locations_locations_csv_upload",
    ],
    # -- event ----------------------------------------------------------------
    "event__subscriptions": [
        "greenlake_delete_events_v1beta1_subscriptions",
        "greenlake_delete_events_v1beta1_system_subscriptions",
        "greenlake_get_events_v1beta1_subscriptions",
        "greenlake_get_events_v1beta1_system_subscriptions",
        "greenlake_patch_events_v1beta1_subscriptions",
        "greenlake_patch_events_v1beta1_system_subscriptions",
        "greenlake_post_events_v1beta1_subscriptions",
        "greenlake_post_events_v1beta1_system_subscriptions",
    ],
    "event__webhooks": [
        "greenlake_delete_events_v1beta1_system_webhooks_id",
        "greenlake_delete_events_v1beta1_webhooks_id",
        "greenlake_get_events_v1beta1_system_webhooks",
        "greenlake_get_events_v1beta1_system_webhooks_id",
        "greenlake_get_events_v1beta1_webhooks",
        "greenlake_get_events_v1beta1_webhooks_id",
        "greenlake_get_events_v1beta1_webhooks_id_recent_deliveries",
        "greenlake_patch_events_v1beta1_system_webhooks_id",
        "greenlake_patch_events_v1beta1_webhooks_id",
        "greenlake_post_events_v1beta1_system_webhooks",
        "greenlake_post_events_v1beta1_webhooks",
        "greenlake_post_events_v1beta1_webhooks_id_delivery_failures_failure_id_retry",
        "greenlake_post_events_v1beta1_webhooks_id_verify",
    ],
    # -- authorization ----------------------------------------------------
    "authorization__groups": [
        "greenlake_delete_workspaces_v1beta1_groups_group_id",
        "greenlake_delete_workspaces_v1beta1_groups_group_id_group_workspaces_group_workspace_id",
        "greenlake_get_workspaces_v1beta1_groups",
        "greenlake_get_workspaces_v1beta1_groups_group_id",
        "greenlake_get_workspaces_v1beta1_groups_group_id_group_workspaces",
        "greenlake_get_workspaces_v1beta1_groups_group_id_group_workspaces_group_workspace_id",
        "greenlake_post_workspaces_v1beta1_groups",
        "greenlake_post_workspaces_v1beta1_groups_group_id_group_workspaces",
        "greenlake_put_workspaces_v1beta1_groups_group_id",
    ],
    "authorization__role_assignments": [
        "greenlake_delete_authorization_v1beta1_role_assignments_id",
        "greenlake_get_authorization_v1beta1_role_assignments",
        "greenlake_get_authorization_v1beta1_role_assignments_id",
        "greenlake_post_authorization_v1beta1_role_assignments",
        "greenlake_put_authorization_v1beta1_role_assignments_id",
    ],
    "authorization__scope_groups": [
        "greenlake_delete_authorization_v1beta1_scope_groups_id",
        "greenlake_delete_authorization_v1beta1_scope_groups_id_scopes_bulk",
        "greenlake_get_authorization_v1beta1_scope_groups",
        "greenlake_get_authorization_v1beta1_scope_groups_id",
        "greenlake_get_authorization_v1beta1_scope_groups_id_scopes",
        "greenlake_post_authorization_v1beta1_scope_groups",
        "greenlake_post_authorization_v1beta1_scope_groups_id_scopes_batch",
        "greenlake_put_authorization_v1beta1_scope_groups_id",
    ],
    # -- service_catalog ------------------------------------------------------
    "service_catalog__media": [
        "greenlake_delete_service_catalog_v1alpha1_service_offers_id_media_media_id",
        "greenlake_get_service_catalog_v1alpha1_media",
        "greenlake_get_service_catalog_v1alpha1_service_offers_id_media",
        "greenlake_get_service_catalog_v1alpha1_service_offers_id_media_media_id",
        "greenlake_patch_service_catalog_v1alpha1_service_offers_id_media_media_id",
        "greenlake_post_service_catalog_v1alpha1_service_offers_id_media",
        "greenlake_post_service_catalog_v1alpha1_service_offers_id_media_media_id_uploaded",
        "greenlake_put_service_catalog_v1alpha1_service_offers_id_media_media_id",
    ],
    "service_catalog__notifications": [
        "greenlake_post_service_catalog_v1beta1_notifications_provision_response",
    ],
    "service_catalog__service_manager": [
        "greenlake_get_service_catalog_v1_per_region_service_managers",
        "greenlake_get_service_catalog_v1_per_region_service_managers_id",
        "greenlake_get_service_catalog_v1_service_managers",
        "greenlake_get_service_catalog_v1_service_managers_id",
    ],
    "service_catalog__service_manager_provision": [
        "greenlake_delete_service_catalog_v1_service_manager_provisions_id",
        "greenlake_get_service_catalog_v1_service_manager_provisions",
        "greenlake_get_service_catalog_v1_service_manager_provisions_id",
        "greenlake_post_service_catalog_v1_service_manager_provisions",
    ],
    "service_catalog__service_offer_regions": [
        "greenlake_delete_service_catalog_v1alpha1_service_offer_regions_id",
        "greenlake_get_service_catalog_v1alpha1_service_offer_regions",
        "greenlake_get_service_catalog_v1alpha1_service_offer_regions_id",
        "greenlake_get_service_catalog_v1beta1_service_offer_regions",
        "greenlake_get_service_catalog_v1beta1_service_offer_regions_id",
        "greenlake_patch_service_catalog_v1alpha1_service_offer_regions_id",
        "greenlake_post_service_catalog_v1alpha1_service_offer_regions",
        "greenlake_post_service_catalog_v1alpha1_service_offer_regions_id_onboarded",
        "greenlake_put_service_catalog_v1alpha1_service_offer_regions_id",
    ],
    "service_catalog__service_offers": [
        "greenlake_delete_service_catalog_v1alpha1_service_offers_id",
        "greenlake_get_service_catalog_v1alpha1_service_offers",
        "greenlake_get_service_catalog_v1alpha1_service_offers_id",
        "greenlake_get_service_catalog_v1beta1_service_offers",
        "greenlake_get_service_catalog_v1beta1_service_offers_id",
        "greenlake_patch_service_catalog_v1alpha1_service_offers_id",
        "greenlake_post_service_catalog_v1alpha1_service_offers",
        "greenlake_post_service_catalog_v1alpha1_service_offers_id_hide",
        "greenlake_post_service_catalog_v1alpha1_service_offers_id_onboarded",
        "greenlake_post_service_catalog_v1alpha1_service_offers_id_publish",
        "greenlake_put_service_catalog_v1alpha1_service_offers_id",
    ],
    "service_catalog__service_offers_migrate": [
        "greenlake_post_service_catalog_v1alpha1_service_offers_migrate",
    ],
    "service_catalog__service_provisions": [
        "greenlake_delete_service_catalog_v1beta1_service_provisions_id",
        "greenlake_get_service_catalog_v1beta1_service_provisions",
        "greenlake_get_service_catalog_v1beta1_service_provisions_id",
        "greenlake_post_service_catalog_v1beta1_service_provisions",
        "greenlake_post_service_catalog_v1beta1_service_provisions_id_retry",
        "greenlake_post_service_catalog_v1beta1_service_provisions_id_retry_unprovision",
        "greenlake_post_service_catalog_v1beta1_service_provisions_id_retry_workspace_transfer",
    ],
    "service_catalog__service_status": [
        "greenlake_get_service_catalog_v1alpha1_health_service_registry",
    ],
    "service_catalog__ui_management": [
        "greenlake_get_service_catalog_v1alpha1_detailed_service_offers_id",
        "greenlake_get_service_catalog_v1alpha1_featured_services",
        "greenlake_get_service_catalog_v1alpha1_my_services",
        "greenlake_get_service_catalog_v1alpha1_service_catalog",
        "greenlake_get_service_catalog_v1beta1_detailed_service_offers_id",
        "greenlake_get_service_catalog_v1beta1_featured_services",
        "greenlake_get_service_catalog_v1beta1_my_services",
        "greenlake_get_service_catalog_v1beta1_recent_services",
        "greenlake_get_service_catalog_v1beta1_service_catalog",
        "greenlake_get_service_catalog_v1beta2_recent_services",
    ],
    "service_catalog__unredacted_service_offer_regions": [
        "greenlake_get_service_catalog_v1alpha1_unredacted_service_offer_regions",
        "greenlake_get_service_catalog_v1alpha1_unredacted_service_offer_regions_id",
    ],
    "service_catalog__unredacted_service_offers": [
        "greenlake_get_service_catalog_v1alpha1_unredacted_service_offers",
        "greenlake_get_service_catalog_v1alpha1_unredacted_service_offers_id",
    ],
    # -- reporting ------------------------------------------------------------
    "reporting__async_operations": [
        "greenlake_get_reporting_v1_async_operations_id",
    ],
    "reporting__report_exports": [
        "greenlake_get_reporting_v1_report_exports_metadata",
        "greenlake_post_reporting_v1_report_exports",
    ],
    "reporting__report_status": [
        "greenlake_get_reporting_v1_statuses",
        "greenlake_get_reporting_v1_statuses_id",
    ],
}
