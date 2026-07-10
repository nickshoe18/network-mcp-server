"""Unit tests for SRX health probe — _probe_srx, _ALL_PLATFORMS, _PROBES."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSRXHealthProbe:
    def test_srx_in_all_platforms(self):
        from hpe_networking_mcp.platforms.health import _ALL_PLATFORMS

        assert "srx" in _ALL_PLATFORMS

    def test_srx_in_probes_dict(self):
        from hpe_networking_mcp.platforms.health import _PROBES

        assert "srx" in _PROBES
        assert callable(_PROBES["srx"])

    async def test_probe_returns_unavailable_when_client_missing(self):
        from hpe_networking_mcp.platforms.health import _probe_srx

        class _FakeCtx:
            lifespan_context = {}

        result = await _probe_srx(_FakeCtx())
        assert result["status"] == "unavailable"
        assert "SRX is not configured" in result["message"]

    async def test_probe_returns_ok_with_facts_when_health_check_succeeds(self):
        from hpe_networking_mcp.platforms.health import _probe_srx

        class _FakeClientOk:
            async def health_check(self) -> dict:
                return {"hostname": "starkwanedge", "model": "SRX300", "version": "21.4R1"}

        class _FakeCtx:
            lifespan_context = {"srx_client": _FakeClientOk()}

        result = await _probe_srx(_FakeCtx())
        assert result["status"] == "ok"
        assert result["hostname"] == "starkwanedge"
        assert result["model"] == "SRX300"

    async def test_probe_returns_degraded_when_health_check_raises(self):
        from hpe_networking_mcp.platforms.health import _probe_srx

        class _FakeClientFail:
            async def health_check(self) -> dict:
                raise RuntimeError("NETCONF connection refused")

        class _FakeCtx:
            lifespan_context = {"srx_client": _FakeClientFail()}

        result = await _probe_srx(_FakeCtx())
        assert result["status"] == "degraded"
        assert result["message"].startswith("SRX probe failed:")
        assert "NETCONF connection refused" in result["message"]
