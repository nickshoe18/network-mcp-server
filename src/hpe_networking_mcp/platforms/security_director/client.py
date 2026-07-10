"""Juniper Security Director Cloud (SD Cloud) API client.

SD Cloud uses a single, static API key over HTTPS -- no OAuth2 flow, no
refresh token, no client secret. Base URL, auth header, and endpoint
paths are confirmed against the real published OpenAPI 3.0 spec
(``security-director-cloud-apis-openapi3json.json``, fetched directly --
Juniper's rendered docs portal is JS-only and doesn't yield real content
to automated fetching, but the static spec export does). That spec covers
SD-WAN/SASE site-and-device orchestration (IAM, Site Management, Device
Groups, Templates, Devices, tunnels, PAC files) -- it does NOT include
firewall security-policy/NAT/address-object CRUD, which may live under a
separate, not-yet-located API surface.
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_context
from loguru import logger

from hpe_networking_mcp.config import SecurityDirectorSecrets
from hpe_networking_mcp.utils.logging import mask_secret

_REQUEST_TIMEOUT = 30.0


class SecurityDirectorAuthError(RuntimeError):
    """Raised when the SD Cloud API key is missing or rejected."""


class SecurityDirectorClient:
    """Async REST API client for Security Director Cloud, static API-key auth.

    Usage in tools::

        client = await get_security_director_client()
        data = await client.get_json("/api/v1/devices")
        return data
    """

    def __init__(self, config: SecurityDirectorSecrets) -> None:
        self._config = config
        self._token: str | None = config.api_key
        self._lock = asyncio.Lock()
        self._http = httpx.AsyncClient(
            base_url=config.base_url,
            timeout=_REQUEST_TIMEOUT,
        )

    @property
    def base_url(self) -> str:
        """Return the configured base URL (host + scheme)."""
        return str(self._http.base_url)

    async def aclose(self) -> None:
        """Close the underlying httpx client. Called from ``server.py:lifespan``."""
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        if self._token is not None:
            return self._token
        async with self._lock:
            if self._token is None:
                await self._login_locked()
            assert self._token is not None
            return self._token

    async def _refresh_token(self) -> str:
        """No refresh endpoint -- SD Cloud API keys are static. Re-validates
        the configured key is still present; a 401 after this means the key
        itself was revoked/rotated in the SD Cloud portal."""
        async with self._lock:
            self._token = None
            await self._login_locked()
            assert self._token is not None
            return self._token

    async def _login_locked(self) -> None:
        token = self._config.api_key
        if not token:
            raise SecurityDirectorAuthError("No api_key configured for Security Director Cloud.")
        self._token = token
        logger.info("Security Director: API key loaded {}", mask_secret(token))

    def _auth_headers(self, token: str) -> dict[str, str]:
        # Confirmed from the live OpenAPI spec (security-director-cloud-apis-openapi3json.json):
        # securitySchemes.ApiKeyAuth = {"type": "apiKey", "name": "x-api-key", "in": "header"}.
        # NOT a Bearer token -- SD Cloud also supports an OAuth2-token variant via
        # x-oauth2-token, unused here since this platform is configured with a static API key.
        return {
            "x-api-key": token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def request(
        self,
        method: str,
        path: str,
        *,
        json_body: Any = None,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> httpx.Response:
        """Send an authenticated request, refreshing the token once on 401."""
        token = await self._ensure_token()
        kwargs: dict[str, Any] = {"headers": self._auth_headers(token)}
        if json_body is not None:
            kwargs["json"] = json_body
        if params:
            kwargs["params"] = params
        if timeout is not None:
            kwargs["timeout"] = timeout

        response = await self._http.request(method, path, **kwargs)
        if response.status_code == 401:
            logger.info("Security Director: 401 on {} {} — refreshing token once", method, path)
            token = await self._refresh_token()
            kwargs["headers"] = self._auth_headers(token)
            response = await self._http.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    async def get_json(self, path: str, **kwargs: Any) -> Any:
        """Shortcut for a GET that returns parsed JSON."""
        response = await self.request("GET", path, **kwargs)
        return response.json()

    async def health_check(self) -> bool:
        """Probe reachability with a minimal, confirmed-real GET (size=1)."""
        await self.get_json("/api/v1/devices", params={"from": 0, "size": 1})
        return True


async def get_security_director_client() -> SecurityDirectorClient:
    """Retrieve the shared client from the lifespan context."""
    ctx = get_context()
    client: SecurityDirectorClient | None = ctx.lifespan_context.get("security_director_client")
    if client is None:
        raise ToolError(
            {
                "status_code": 503,
                "message": "Security Director API client not available. Check your credentials.",
            }
        )
    return client


def format_http_error(exc: BaseException) -> dict[str, Any]:
    """Shape any exception into a consistent dict for tool returns."""
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
        text = exc.response.text[:500]
        try:
            body: Any = exc.response.json()
        except (ValueError, json.JSONDecodeError):
            body = text
        return {"status_code": status, "message": str(exc), "body": body}
    return {"status_code": 0, "message": str(exc), "body": None}
