"""Tests for Classic Central's new group_config tools and the devices.py aps bug fix.

``classic_central_get_group_config`` wraps the confirmed-real
``GET /configuration/v1/ap_cli/{group_name}`` endpoint; ``classic_central_get_devices``
had a real bug (device_type='aps' called the wrong API version) fixed alongside it.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

pytestmark = pytest.mark.unit


class _FakeClient:
    def __init__(self, response):
        self._response = response
        self.calls: list[tuple[str, dict | None]] = []

    async def get_json(self, path, **kwargs):
        self.calls.append((path, kwargs.get("params")))
        return self._response


class TestGetGroupConfig:
    async def test_calls_ap_cli_endpoint_with_group_name(self):
        from hpe_networking_mcp.platforms.classic_central.tools import group_config

        fake = _FakeClient(["vlan Users 60", "  max-tx-power 19"])
        with patch.object(group_config, "get_classic_central_client", AsyncMock(return_value=fake)):
            result = await group_config.classic_central_get_group_config(ctx=None, group_name="Wayne Enterprises")

        assert result == ["vlan Users 60", "  max-tx-power 19"]
        assert fake.calls[0][0] == "/configuration/v1/ap_cli/Wayne Enterprises"

    async def test_error_is_formatted_not_raised(self):
        from hpe_networking_mcp.platforms.classic_central.tools import group_config

        class _FailingClient:
            async def get_json(self, path, **kwargs):
                raise RuntimeError("boom")

        with patch.object(group_config, "get_classic_central_client", AsyncMock(return_value=_FailingClient())):
            result = await group_config.classic_central_get_group_config(ctx=None, group_name="unprovisioned")

        assert isinstance(result, str)
        assert "boom" in result


class TestGetGroups:
    async def test_extracts_data_key(self):
        from hpe_networking_mcp.platforms.classic_central.tools import group_config

        payload = {"data": [{"group": "Wayne Enterprises", "group_attributes": {"template_group": False}}], "total": 1}
        fake = _FakeClient(payload)
        with patch.object(group_config, "get_classic_central_client", AsyncMock(return_value=fake)):
            result = await group_config.classic_central_get_groups(ctx=None)

        assert result == payload["data"]
        assert fake.calls[0][0] == "/configuration/v1/groups"


class TestGetDevicesApsVersionFix:
    """Regression test for the confirmed real bug: 'aps' needs /monitoring/v2/, not v1."""

    async def test_aps_uses_v2(self):
        from hpe_networking_mcp.platforms.classic_central.tools import devices

        fake = _FakeClient({"aps": [{"name": "Garage"}]})
        with patch.object(devices, "get_classic_central_client", AsyncMock(return_value=fake)):
            await devices.classic_central_get_devices(ctx=None, device_type="aps")

        assert fake.calls[0][0] == "/monitoring/v2/aps"

    async def test_switches_still_uses_v1(self):
        from hpe_networking_mcp.platforms.classic_central.tools import devices

        fake = _FakeClient({"switches": []})
        with patch.object(devices, "get_classic_central_client", AsyncMock(return_value=fake)):
            await devices.classic_central_get_devices(ctx=None, device_type="switches")

        assert fake.calls[0][0] == "/monitoring/v1/switches"

    async def test_gateways_still_uses_v1(self):
        from hpe_networking_mcp.platforms.classic_central.tools import devices

        fake = _FakeClient({"gateways": []})
        with patch.object(devices, "get_classic_central_client", AsyncMock(return_value=fake)):
            await devices.classic_central_get_devices(ctx=None, device_type="gateways")

        assert fake.calls[0][0] == "/monitoring/v1/gateways"
