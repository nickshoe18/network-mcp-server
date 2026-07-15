"""Classic Aruba Central API client — OAuth2 refresh-token flow.

Classic Central (the legacy Aruba Central API, distinct from New Central's
client-credentials OAuth2) issues short-lived access tokens via a
refresh-token grant against ``/oauth2/token``, and **rotates the refresh
token on every use** — the response includes a new ``refresh_token`` that
must be used for the *next* refresh, invalidating the one just used.

This means the refresh token in ``secrets/classic_central_refresh_token``
goes stale the moment this client uses it once. We keep the current
refresh token in memory and best-effort persist each new one back to the
secrets file, so a server restart can pick up the latest token. If the
secrets mount is read-only (e.g. Docker Compose secrets), that write will
fail — logged as a warning, not fatal — and whoever manages the deployment
will need to regenerate the refresh token from Central's UI after a
restart. See ``platforms/classic_central`` docs / CLAUDE.md for the
operational note.
"""

from __future__ import annotations

import asyncio
import json
import time
from pathlib import Path
from typing import Any

import httpx
from fastmcp.exceptions import ToolError
from fastmcp.server.dependencies import get_context
from loguru import logger

from hpe_networking_mcp.config import ClassicCentralSecrets
from hpe_networking_mcp.utils.logging import mask_secret

_REQUEST_TIMEOUT = 30.0
_AUTH_TIMEOUT = 10.0
# Refresh a little before actual expiry to avoid racing a 401.
_EXPIRY_SAFETY_MARGIN = 60.0


class ClassicCentralAuthError(RuntimeError):
    """Raised when the Classic Central OAuth2 refresh handshake fails."""


class ClassicCentralClient:
    """Async REST client for Classic Central with refresh-token auth.

    Usage in tools::

        client = await get_classic_central_client()
        data = await client.get_json("/monitoring/v1/aps")
        return data
    """

    def __init__(self, config: ClassicCentralSecrets) -> None:
        self._config = config
        self._access_token: str | None = None
        self._refresh_token: str = config.refresh_token
        self._expires_at: float = 0.0
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
        """Return a valid access token, refreshing if expired or absent."""
        if self._access_token is not None and time.monotonic() < self._expires_at:
            return self._access_token
        async with self._lock:
            if self._access_token is None or time.monotonic() >= self._expires_at:
                await self._refresh_locked()
            assert self._access_token is not None
            return self._access_token

    async def _refresh_token_force(self) -> str:
        """Force-refresh the access token under the lock (used on 401)."""
        async with self._lock:
            await self._refresh_locked()
            assert self._access_token is not None
            return self._access_token

    async def _refresh_locked(self) -> None:
        """Exchange the current refresh token for a new access + refresh token pair.

        Caller must hold ``self._lock``.
        """
        try:
            response = await self._http.post(
                "/oauth2/token",
                params={"client_id": self._config.client_id},
                data={
                    "grant_type": "refresh_token",
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                    "refresh_token": self._refresh_token,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                timeout=_AUTH_TIMEOUT,
            )
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise ClassicCentralAuthError(
                f"Classic Central token refresh failed: {exc}. "
                "The refresh token may have rotated past what's in "
                "secrets/classic_central_refresh_token -- regenerate it "
                "from Central's API Gateway UI."
            ) from exc

        access_token = body.get("access_token")
        new_refresh_token = body.get("refresh_token")
        expires_in = body.get("expires_in", 7200)
        if not access_token or not new_refresh_token:
            raise ClassicCentralAuthError(f"Classic Central token response missing access_token/refresh_token: {body}")

        self._access_token = access_token
        self._refresh_token = new_refresh_token
        self._expires_at = time.monotonic() + float(expires_in) - _EXPIRY_SAFETY_MARGIN
        logger.info(
            "Classic Central: token refreshed {} (expires in {}s)",
            mask_secret(access_token),
            expires_in,
        )
        self._persist_refresh_token(new_refresh_token)

    def _persist_refresh_token(self, refresh_token: str) -> None:
        """Best-effort write the rotated refresh token back to its secrets file.

        Docker Compose secrets mounts are read-only, so this commonly fails
        in production -- that's expected and only logged, not raised. Local
        (non-Docker) runs against a writable ``secrets/`` directory benefit
        from this so restarts keep working without manual intervention.
        """
        path = self._config.refresh_token_path
        if not path:
            return
        try:
            Path(path).write_text(refresh_token)
            logger.debug("Classic Central: persisted rotated refresh token to {}", path)
        except OSError as e:
            logger.warning(
                "Classic Central: could not persist rotated refresh token to {} ({}). "
                "If the server restarts before a fresh token is regenerated, "
                "auth will fail -- regenerate from Central's API Gateway UI.",
                path,
                e,
            )

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {token}",
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
            logger.info("Classic Central: 401 on {} {} — refreshing token once", method, path)
            token = await self._refresh_token_force()
            kwargs["headers"] = self._auth_headers(token)
            response = await self._http.request(method, path, **kwargs)
        response.raise_for_status()
        return response

    async def get_json(self, path: str, **kwargs: Any) -> Any:
        """Shortcut for a GET that returns parsed JSON."""
        response = await self.request("GET", path, **kwargs)
        return response.json()

    async def health_check(self) -> bool:
        """Probe credentials by acquiring/validating an access token."""
        await self._ensure_token()
        return True


async def get_classic_central_client() -> ClassicCentralClient:
    """Retrieve the shared client from the lifespan context."""
    ctx = get_context()
    client: ClassicCentralClient | None = ctx.lifespan_context.get("classic_central_client")
    if client is None:
        raise ToolError(
            {
                "status_code": 503,
                "message": "Classic Central API client not available. Check your credentials.",
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
