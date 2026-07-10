"""Tests for the plain HTTP /livez, /readyz, /healthz endpoints.

Deliberately separate from ``platforms/health.py``'s MCP-protocol ``health``
tool -- these routes must answer with zero MCP negotiation and zero
upstream platform calls, so an outage in Mist/Central/etc. can never flip
a container's Kubernetes/Docker health probe. Driven directly against the
FastMCP instance's ASGI app via httpx, bypassing the real ``lifespan()``
(which requires full platform config) entirely -- these routes don't
depend on it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import httpx
import pytest
from fastmcp import FastMCP

from hpe_networking_mcp.health_routes import mark_ready, register_health_routes


@dataclass
class _FakeConfig:
    enabled_platforms: list[str] = field(default_factory=lambda: ["mist", "central"])


def _make_client(mcp: FastMCP) -> httpx.AsyncClient:
    app = mcp.http_app()
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")


@pytest.mark.unit
class TestLivez:
    async def test_always_ok(self) -> None:
        mcp = FastMCP("probe-livez")
        register_health_routes(mcp, _FakeConfig())
        async with _make_client(mcp) as client:
            response = await client.get("/livez")
        assert response.status_code == 200
        assert response.text == "ok\n"

    async def test_ok_even_before_ready(self) -> None:
        """Liveness must never depend on readiness -- a slow startup should
        not cause Kubernetes to kill the pod."""
        mcp = FastMCP("probe-livez-2")
        register_health_routes(mcp, _FakeConfig())
        async with _make_client(mcp) as client:
            response = await client.get("/livez")
        assert response.status_code == 200


@pytest.mark.unit
class TestReadyz:
    async def test_503_before_ready(self) -> None:
        mcp = FastMCP("probe-readyz")
        register_health_routes(mcp, _FakeConfig())
        async with _make_client(mcp) as client:
            response = await client.get("/readyz")
        assert response.status_code == 503
        assert response.text == "starting\n"

    async def test_200_after_mark_ready(self) -> None:
        mcp = FastMCP("probe-readyz-2")
        register_health_routes(mcp, _FakeConfig())
        mark_ready(mcp)
        async with _make_client(mcp) as client:
            response = await client.get("/readyz")
        assert response.status_code == 200
        assert response.text == "ok\n"

    async def test_mark_ready_on_unregistered_mcp_is_a_noop(self) -> None:
        """mark_ready() is called unconditionally from lifespan(); it must
        not raise if register_health_routes() was somehow never called."""
        mcp = FastMCP("probe-readyz-unregistered")
        mark_ready(mcp)  # must not raise


@pytest.mark.unit
class TestHealthz:
    async def test_shape_before_ready(self) -> None:
        mcp = FastMCP("probe-healthz")
        register_health_routes(mcp, _FakeConfig(enabled_platforms=["mist", "central", "uxi"]))
        async with _make_client(mcp) as client:
            response = await client.get("/healthz")
        assert response.status_code == 200
        body = response.json()
        assert body["service"] == "hpe-networking-mcp"
        assert body["status"] == "starting"
        assert body["platforms"] == ["mist", "central", "uxi"]
        assert isinstance(body["uptime_seconds"], (int, float))
        assert isinstance(body["version"], str) and body["version"]

    async def test_status_ok_after_ready(self) -> None:
        mcp = FastMCP("probe-healthz-2")
        register_health_routes(mcp, _FakeConfig())
        mark_ready(mcp)
        async with _make_client(mcp) as client:
            response = await client.get("/healthz")
        assert response.json()["status"] == "ok"

    async def test_does_not_call_out_to_platforms(self) -> None:
        """healthz must stay shallow -- it must not import or invoke
        platforms/health.py's run_probes, which makes live API calls."""
        import inspect

        from hpe_networking_mcp import health_routes

        source = inspect.getsource(health_routes)
        assert "run_probes" not in source
        assert "_probe_" not in source


@pytest.mark.unit
class TestServerWiring:
    def test_lifespan_calls_mark_ready(self) -> None:
        import inspect

        from hpe_networking_mcp import server

        source = inspect.getsource(server.lifespan)
        assert "mark_ready" in source

    def test_create_server_registers_health_routes(self) -> None:
        import inspect

        from hpe_networking_mcp import server

        source = inspect.getsource(server.create_server)
        assert "register_health_routes" in source
