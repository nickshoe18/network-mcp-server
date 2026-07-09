"""Tests for the Classic Central platform module.

Modeled on ``test_platform_template.py`` -- guards the structural
conventions (registry entry, write-tag wiring, importability) that every
real platform must satisfy, plus a couple of Classic-Central-specific
checks (it's genuinely wired into server.py/config.py/health.py, unlike
the template).
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestClassicCentralImportable:
    def test_package_importable(self):
        import hpe_networking_mcp.platforms.classic_central  # noqa: F401

    def test_register_tools_callable(self):
        from hpe_networking_mcp.platforms.classic_central import register_tools

        assert callable(register_tools)

    def test_tool_decorator_exposed(self):
        from hpe_networking_mcp.platforms.classic_central._registry import tool

        assert callable(tool)

    def test_annotation_constants_exposed(self):
        from hpe_networking_mcp.platforms.classic_central.tools import READ_ONLY, WRITE, WRITE_DELETE

        assert READ_ONLY.readOnlyHint is True
        assert READ_ONLY.idempotentHint is True
        assert READ_ONLY.destructiveHint is False

        assert WRITE.readOnlyHint is False
        assert WRITE.destructiveHint is False

        assert WRITE_DELETE.readOnlyHint is False
        assert WRITE_DELETE.destructiveHint is True

    def test_tool_modules_importable(self):
        from hpe_networking_mcp.platforms.classic_central.tools import devices, variables  # noqa: F401

    def test_client_module_importable(self):
        from hpe_networking_mcp.platforms.classic_central.client import (
            ClassicCentralAuthError,
            ClassicCentralClient,
            format_http_error,
            get_classic_central_client,
        )

        assert callable(get_classic_central_client)
        assert callable(format_http_error)
        assert isinstance(ClassicCentralAuthError("x"), RuntimeError)
        assert isinstance(ClassicCentralClient, type)


@pytest.mark.unit
class TestClassicCentralConventions:
    def test_tools_dict_shape(self):
        from hpe_networking_mcp.platforms.classic_central import TOOLS

        assert isinstance(TOOLS, dict)
        for category, names in TOOLS.items():
            assert isinstance(category, str)
            assert isinstance(names, list)
            for name in names:
                assert isinstance(name, str)
                assert name.startswith("classic_central_")

    def test_registered_in_registries(self):
        from hpe_networking_mcp.platforms._common.tool_registry import REGISTRIES

        assert "classic_central" in REGISTRIES

    def test_write_tag_dict(self):
        from hpe_networking_mcp.platforms._common.tool_registry import _WRITE_TAG_BY_PLATFORM

        assert "classic_central" in _WRITE_TAG_BY_PLATFORM
        assert "classic_central_write" in _WRITE_TAG_BY_PLATFORM["classic_central"]

    def test_gate_config_attr(self):
        from hpe_networking_mcp.platforms._common.tool_registry import _GATE_CONFIG_ATTR

        assert _GATE_CONFIG_ATTR.get("classic_central") == "enable_classic_central_write_tools"


@pytest.mark.unit
class TestClassicCentralWiredIntoServer:
    """Unlike the template, Classic Central must actually be wired in."""

    def test_referenced_in_server(self):
        import inspect

        from hpe_networking_mcp import server

        source = inspect.getsource(server)
        assert "config.classic_central" in source
        assert "_register_classic_central_tools" in source

    def test_referenced_in_config(self):
        import inspect

        from hpe_networking_mcp import config

        source = inspect.getsource(config)
        assert "_load_classic_central" in source
        assert "ClassicCentralSecrets" in source

    def test_registered_in_health_probes(self):
        from hpe_networking_mcp.platforms.health import _ALL_PLATFORMS, _PROBES

        assert "classic_central" in _ALL_PLATFORMS
        assert "classic_central" in _PROBES


@pytest.mark.unit
class TestClassicCentralSecretsDataclass:
    def test_fields(self):
        from hpe_networking_mcp.config import ClassicCentralSecrets

        secrets = ClassicCentralSecrets(
            base_url="https://example.invalid",
            client_id="id",
            client_secret="secret",
            customer_id="cust",
            refresh_token="token",
        )
        assert secrets.base_url == "https://example.invalid"
        assert secrets.refresh_token_path is None
