"""Juniper SRX NETCONF-over-SSH client (via PyEZ / ``junos-eznc``).

Read-only first pass -- no config-changing (commit) capability yet, see
``config.py:SRXSecrets``. PyEZ's ``Device``/``cli()`` calls are
synchronous (blocking SSH I/O), so every call here runs inside
``asyncio.to_thread()`` to stay compatible with the rest of this async
server. Auth reuses the device's normal SSH username/password -- NETCONF
is a subsystem on the same SSH session (``set system services netconf
ssh``), not a separate credential system.

NOT YET LIVE-VERIFIED against a real device. StarkWANEdge (SRX300) had
NETCONF disabled at the time this platform was scaffolded (it was just
moved out of Mist management into Security Director Cloud, which has no
firewall policy/NAT/address-book API -- this platform exists to fill that
gap via direct CLI access). Treat the RPC/CLI behavior here as "PyEZ's
documented API used as documented," not "confirmed against a live SRX,"
until the health probe reports ok in a real deployment.
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_context
from jnpr.junos import Device
from jnpr.junos.exception import ConnectError, RpcError
from loguru import logger

from hpe_networking_mcp.config import SRXSecrets
from hpe_networking_mcp.utils.logging import mask_secret

_CONNECT_PROBE_TIMEOUT = 30


class SRXConnectionError(RuntimeError):
    """Raised when the NETCONF session can't be established, or a
    disallowed (non-``show``) command is attempted."""


class SRXClient:
    """Thin async wrapper around a PyEZ ``Device`` NETCONF session.

    Usage in tools::

        client = await get_srx_client()
        facts = await client.get_facts()
        text = await client.show("show configuration security policies")
    """

    def __init__(self, config: SRXSecrets) -> None:
        self._config = config
        self._dev: Device | None = None
        self._lock = asyncio.Lock()

    async def _open_new_session(self) -> Device:
        dev = Device(
            host=self._config.host,
            port=self._config.port,
            user=self._config.username,
            password=self._config.password,
            gather_facts=True,
            auto_probe=_CONNECT_PROBE_TIMEOUT,
        )
        await asyncio.to_thread(dev.open)
        logger.info(
            "SRX: NETCONF session opened to {} (user: {})",
            self._config.host,
            mask_secret(self._config.username),
        )
        return dev

    async def _ensure_open(self) -> Device:
        if self._dev is not None and self._dev.connected:
            return self._dev
        async with self._lock:
            if self._dev is None or not self._dev.connected:
                self._dev = await self._open_new_session()
            return self._dev

    async def aclose(self) -> None:
        """Close the NETCONF session. Called from ``server.py:lifespan``."""
        if self._dev is not None:
            try:
                await asyncio.to_thread(self._dev.close)
            except Exception as e:  # noqa: BLE001 -- shutdown must not raise
                logger.warning("SRX: close failed during shutdown -- {}", e)
            self._dev = None

    async def get_facts(self) -> dict[str, Any]:
        """Return device facts (hostname, model, version, serial number, ...)."""
        dev = await self._ensure_open()
        return dict(dev.facts)

    async def show(self, command: str) -> str:
        """Run a read-only ``show`` CLI command and return its text output.

        Restricted to commands starting with ``show`` -- this is a
        read-only-first-pass platform; no config-changing RPCs exist yet.
        Covers both operational queries (``show security policies``,
        ``show route``) and full/hierarchy-filtered config export
        (``show configuration``, ``show configuration security nat``) --
        Junos's own CLI already does the filtering, so no separate
        NETCONF get-config filter path is needed.
        """
        normalized = command.strip()
        if not normalized.lower().startswith("show"):
            raise SRXConnectionError(f"Only 'show' commands are permitted, got: {command!r}")

        dev = await self._ensure_open()
        try:
            return await asyncio.to_thread(dev.cli, normalized, warning=False)
        except RpcError:
            # Session may have gone stale -- reopen once and retry.
            async with self._lock:
                self._dev = await self._open_new_session()
            return await asyncio.to_thread(self._dev.cli, normalized, warning=False)

    async def health_check(self) -> dict[str, Any]:
        """Probe reachability by opening a session and reading facts."""
        facts = await self.get_facts()
        return {
            "hostname": facts.get("hostname"),
            "model": facts.get("model"),
            "version": facts.get("version"),
        }


async def get_srx_client() -> SRXClient:
    """Retrieve the shared client from the lifespan context."""
    ctx = get_context()
    client: SRXClient | None = ctx.lifespan_context.get("srx_client")
    if client is None:
        raise ToolError(
            {
                "status_code": 503,
                "message": "SRX NETCONF client not available. Check your credentials.",
            }
        )
    return client


def format_srx_error(exc: BaseException) -> dict[str, Any]:
    """Shape any exception into a consistent dict for tool returns."""
    if isinstance(exc, ConnectError):
        return {"status_code": 0, "message": f"NETCONF connection failed: {exc}", "body": None}
    if isinstance(exc, SRXConnectionError):
        return {"status_code": 0, "message": str(exc), "body": None}
    return {"status_code": 0, "message": str(exc), "body": None}
