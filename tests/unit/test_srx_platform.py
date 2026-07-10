"""Tests for the SRX platform module.

Modeled on ``test_security_director_platform.py`` -- guards the
structural conventions (registry entry, importability) every real
platform must satisfy.
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSRXImportable:
    def test_package_importable(self):
        import hpe_networking_mcp.platforms.srx  # noqa: F401

    def test_register_tools_callable(self):
        from hpe_networking_mcp.platforms.srx import register_tools

        assert callable(register_tools)

    def test_tool_decorator_exposed(self):
        from hpe_networking_mcp.platforms.srx._registry import tool

        assert callable(tool)

    def test_annotation_constants_exposed(self):
        from hpe_networking_mcp.platforms.srx.tools import READ_ONLY

        assert READ_ONLY.readOnlyHint is True
        assert READ_ONLY.idempotentHint is True
        assert READ_ONLY.destructiveHint is False

    def test_tool_modules_importable(self):
        from hpe_networking_mcp.platforms.srx.tools import device  # noqa: F401

    def test_client_module_importable(self):
        from hpe_networking_mcp.platforms.srx.client import (
            SRXClient,
            SRXConnectionError,
            format_srx_error,
            get_srx_client,
        )

        assert callable(get_srx_client)
        assert callable(format_srx_error)
        assert isinstance(SRXConnectionError("x"), RuntimeError)
        assert isinstance(SRXClient, type)


@pytest.mark.unit
class TestSRXConventions:
    def test_tools_dict_shape(self):
        from hpe_networking_mcp.platforms.srx import TOOLS

        assert isinstance(TOOLS, dict)
        for category, names in TOOLS.items():
            assert isinstance(category, str)
            assert isinstance(names, list)
            for name in names:
                assert isinstance(name, str)
                assert name.startswith("srx_")

    def test_registered_in_registries(self):
        from hpe_networking_mcp.platforms._common.tool_registry import REGISTRIES

        assert "srx" in REGISTRIES

    def test_no_write_gate_yet(self):
        """SRX is read-only today -- no write tags/gate attr."""
        from hpe_networking_mcp.platforms._common.tool_registry import _GATE_CONFIG_ATTR, _WRITE_TAG_BY_PLATFORM

        assert _WRITE_TAG_BY_PLATFORM.get("srx") == set()
        assert _GATE_CONFIG_ATTR.get("srx") is None


@pytest.mark.unit
class TestSRXWiredIntoServer:
    def test_referenced_in_server(self):
        import inspect

        from hpe_networking_mcp import server

        source = inspect.getsource(server)
        assert "config.srx" in source
        assert "_register_srx_tools" in source

    def test_referenced_in_config(self):
        import inspect

        from hpe_networking_mcp import config

        source = inspect.getsource(config)
        assert "_load_srx" in source
        assert "SRXSecrets" in source

    def test_registered_in_health_probes(self):
        from hpe_networking_mcp.platforms.health import _ALL_PLATFORMS, _PROBES

        assert "srx" in _ALL_PLATFORMS
        assert "srx" in _PROBES


@pytest.mark.unit
class TestSRXSecretsDataclass:
    def test_fields(self):
        from hpe_networking_mcp.config import SRXSecrets

        secrets = SRXSecrets(host="srx.example.invalid", username="admin", password="secret")
        assert secrets.host == "srx.example.invalid"
        assert secrets.username == "admin"
        assert secrets.password == "secret"
        assert secrets.port == 830

    def test_port_override(self):
        from hpe_networking_mcp.config import SRXSecrets

        secrets = SRXSecrets(host="srx.example.invalid", username="admin", password="secret", port=22)
        assert secrets.port == 22
