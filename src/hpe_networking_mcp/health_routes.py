"""Plain HTTP health endpoints for Kubernetes/Docker orchestrators.

Deliberately separate from the MCP-protocol ``health`` tool
(``platforms/health.py``): these three routes answer without any MCP
client negotiation and without ever calling an upstream platform API, so
a Mist/Central/etc. outage can never flip a container's liveness or
readiness probe. Deep, per-platform reachability stays exclusively
behind the ``health`` tool, reachable only via a real MCP client.

Ported from upstream ``nowireless4u/hpe-networking-mcp`` (v3.5.2.0,
"Kubernetes/Docker-friendly HTTP health endpoints").
"""

from __future__ import annotations

import time
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _pkg_version
from typing import Any
from weakref import WeakKeyDictionary

from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response

from hpe_networking_mcp.config import ServerConfig

# Keyed by the FastMCP instance itself (not id()) so state is naturally
# reclaimed if the server instance is garbage collected -- relevant in
# tests, which may construct many short-lived servers.
_STATE: WeakKeyDictionary[FastMCP, dict[str, Any]] = WeakKeyDictionary()


def mark_ready(mcp: FastMCP) -> None:
    """Flip the readiness flag once lifespan startup has completed.

    Called from ``server.py:lifespan()`` right before ``yield`` -- after
    platform clients are initialized and the startup probe loop has run,
    but this flag does not depend on any probe having succeeded. A
    platform being degraded at startup is a ``health`` tool concern, not
    a readiness concern.
    """
    state = _STATE.get(mcp)
    if state is not None:
        state["ready"] = True


def _version() -> str:
    try:
        return _pkg_version("hpe-networking-mcp")
    except PackageNotFoundError:
        return "unknown"


def register_health_routes(mcp: FastMCP, config: ServerConfig) -> None:
    """Register plain HTTP ``/livez``, ``/readyz``, ``/healthz`` routes.

    These require no MCP protocol negotiation, so Kubernetes/Docker can
    probe them directly with a plain HTTP client:

    - ``/livez``  -- always ``200 ok``. Process-alive only.
    - ``/readyz`` -- ``503 starting`` until lifespan startup completes,
      then ``200 ok``. A one-time startup gate, not an ongoing
      dependency probe.
    - ``/healthz`` -- shallow JSON status (service, version, enabled
      platform names, uptime). No live platform API calls.
    """
    _STATE[mcp] = {"ready": False, "started_at": time.monotonic()}

    @mcp.custom_route("/livez", methods=["GET"])
    async def livez(request: Request) -> Response:
        return PlainTextResponse("ok\n")

    @mcp.custom_route("/readyz", methods=["GET"])
    async def readyz(request: Request) -> Response:
        state = _STATE.get(mcp)
        if state is not None and state["ready"]:
            return PlainTextResponse("ok\n")
        return PlainTextResponse("starting\n", status_code=503)

    @mcp.custom_route("/healthz", methods=["GET"])
    async def healthz(request: Request) -> Response:
        state = _STATE.get(mcp) or {"ready": False, "started_at": time.monotonic()}
        return JSONResponse(
            {
                "service": "hpe-networking-mcp",
                "version": _version(),
                "status": "ok" if state["ready"] else "starting",
                "platforms": list(config.enabled_platforms),
                "uptime_seconds": round(time.monotonic() - state["started_at"], 1),
            }
        )
