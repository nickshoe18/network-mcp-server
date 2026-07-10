"""Tests for the Security Director platform module.

Modeled on ``test_classic_central_platform.py`` -- guards the structural
conventions (registry entry, importability) every real platform must
satisfy.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSecurityDirectorImportable:
    def test_package_importable(self):
        import hpe_networking_mcp.platforms.security_director  # noqa: F401

    def test_register_tools_callable(self):
        from hpe_networking_mcp.platforms.security_director import register_tools

        assert callable(register_tools)

    def test_tool_decorator_exposed(self):
        from hpe_networking_mcp.platforms.security_director._registry import tool

        assert callable(tool)

    def test_annotation_constants_exposed(self):
        from hpe_networking_mcp.platforms.security_director.tools import READ_ONLY

        assert READ_ONLY.readOnlyHint is True
        assert READ_ONLY.idempotentHint is True
        assert READ_ONLY.destructiveHint is False

    def test_tool_modules_importable(self):
        from hpe_networking_mcp.platforms.security_director.tools import devices, sites  # noqa: F401

    def test_client_module_importable(self):
        from hpe_networking_mcp.platforms.security_director.client import (
            SecurityDirectorAuthError,
            SecurityDirectorClient,
            format_http_error,
            get_security_director_client,
        )

        assert callable(get_security_director_client)
        assert callable(format_http_error)
        assert isinstance(SecurityDirectorAuthError("x"), RuntimeError)
        assert isinstance(SecurityDirectorClient, type)


@pytest.mark.unit
class TestSecurityDirectorConventions:
    def test_tools_dict_shape(self):
        from hpe_networking_mcp.platforms.security_director import TOOLS

        assert isinstance(TOOLS, dict)
        for category, names in TOOLS.items():
            assert isinstance(category, str)
            assert isinstance(names, list)
            for name in names:
                assert isinstance(name, str)
                assert name.startswith("security_director_")

    def test_registered_in_registries(self):
        from hpe_networking_mcp.platforms._common.tool_registry import REGISTRIES

        assert "security_director" in REGISTRIES

    def test_no_write_gate_yet(self):
        """Security Director is read-only today -- no write tags/gate attr."""
        from hpe_networking_mcp.platforms._common.tool_registry import _GATE_CONFIG_ATTR, _WRITE_TAG_BY_PLATFORM

        assert _WRITE_TAG_BY_PLATFORM.get("security_director") == set()
        assert _GATE_CONFIG_ATTR.get("security_director") is None


@pytest.mark.unit
class TestSecurityDirectorWiredIntoServer:
    def test_referenced_in_server(self):
        import inspect

        from hpe_networking_mcp import server

        source = inspect.getsource(server)
        assert "config.security_director" in source
        assert "_register_security_director_tools" in source

    def test_referenced_in_config(self):
        import inspect

        from hpe_networking_mcp import config

        source = inspect.getsource(config)
        assert "_load_security_director" in source
        assert "SecurityDirectorSecrets" in source

    def test_registered_in_health_probes(self):
        from hpe_networking_mcp.platforms.health import _ALL_PLATFORMS, _PROBES

        assert "security_director" in _ALL_PLATFORMS
        assert "security_director" in _PROBES


@pytest.mark.unit
class TestSecurityDirectorSecretsDataclass:
    def test_fields(self):
        from hpe_networking_mcp.config import SecurityDirectorSecrets

        secrets = SecurityDirectorSecrets(base_url="https://example.invalid", api_key="key")
        assert secrets.base_url == "https://example.invalid"
        assert secrets.api_key == "key"
