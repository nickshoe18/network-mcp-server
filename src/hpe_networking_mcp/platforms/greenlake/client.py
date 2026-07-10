# (c) Copyright 2025 Hewlett Packard Enterprise Development LP
"""Async HTTP client for the HPE GreenLake API.

Ported from the per-service ``AuditLogsHttpClient`` /
``DevicesHttpClient`` etc. into a single shared
``GreenLakeHttpClient``.
"""

from __future__ import annotations

import asyncio
import json as _json
from typing import TYPE_CHECKING, Any
from urllib.parse import urlsplit

import httpx
from fastmcp.exceptions import ToolError
from loguru import logger

from hpe_networking_mcp.platforms.greenlake.auth import TokenManager

if TYPE_CHECKING:
    from fastmcp import Context

# Async-operation polling (GreenLake writes return 202 + Location -> poll).
_ASYNC_POLL_INTERVAL_SECS = 2.0
_ASYNC_POLL_MAX_ATTEMPTS = 60  # ~120 s ceiling
_ASYNC_TERMINAL = frozenset({"SUCCEEDED", "FAILED", "TIMEOUT", "TIMEDOUT"})


class GreenLakeHttpClient:
    """Async HTTP client with automatic OAuth2 token management."""

    def __init__(self, token_manager: TokenManager, base_url: str) -> None:
        self.token_manager = token_manager
        self.base_url = base_url.rstrip("/")

        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_connections=10, max_keepalive_connections=5),
        )

    # -- HTTP verbs --------------------------------------------------------

    async def get(
        self,
        endpoint: str,
        params: dict[str, Any] | None = None,
        additional_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated GET request."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers()
        if additional_headers:
            headers.update(additional_headers)

        logger.debug("GET {}", url)
        try:
            response = await self.client.get(url, headers=headers, params=params)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error {}: {}",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Request failed: {}", str(e))
            raise

    async def post(
        self,
        endpoint: str,
        data: dict[str, Any] | None = None,
        additional_headers: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Perform an authenticated POST request."""
        url = f"{self.base_url}{endpoint}"
        headers = self._get_auth_headers()
        if additional_headers:
            headers.update(additional_headers)

        logger.debug("POST {}", url)
        try:
            response = await self.client.post(url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()  # type: ignore[no-any-return]
        except httpx.HTTPStatusError as e:
            logger.error(
                "HTTP error {}: {}",
                e.response.status_code,
                e.response.text,
            )
            raise
        except Exception as e:
            logger.error("Request failed: {}", str(e))
            raise

    async def request_raw(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        json_body: Any | None = None,
    ) -> httpx.Response:
        """Perform an authenticated request for any verb; return the raw response.

        Does NOT call ``raise_for_status()`` -- the caller (``greenlake_request``)
        inspects the status code so it can drive the 202 + async-operation poll.
        """
        url = f"{self.base_url}{endpoint}"
        req_headers = self._get_auth_headers()
        if headers:
            req_headers.update(headers)
        logger.debug("{} (raw) {}", method.upper(), url)
        return await self.client.request(method.upper(), url, headers=req_headers, params=params, json=json_body)

    # -- helpers -----------------------------------------------------------

    def _get_auth_headers(self) -> dict[str, str]:
        """Build auth + accept headers, refreshing if needed."""
        headers: dict[str, str] = self.token_manager.get_auth_headers()
        headers["Accept"] = "application/json"
        return headers

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self.client.aclose()

    async def __aenter__(self) -> GreenLakeHttpClient:
        return self

    async def __aexit__(
        self,
        exc_type: object,
        exc_val: object,
        exc_tb: object,
    ) -> None:
        await self.close()


def get_greenlake_client(ctx: Context) -> GreenLakeHttpClient:
    """Return a configured GreenLake client, or raise a clear 503 ToolError.

    GreenLake is optional: when its Docker secrets are absent or startup
    failed, ``server.py`` stores ``greenlake_token_manager = None`` and
    ``config.greenlake`` is ``None``. Tools that dereference those directly
    would crash with an opaque ``AttributeError``; this helper checks both
    up front and raises an actionable ``ToolError`` instead, so a
    disabled/failed integration produces a recoverable "not configured"
    response rather than an internal error.

    Args:
        ctx: The FastMCP request context.

    Returns:
        A ``GreenLakeHttpClient`` bound to the configured base URL.

    Raises:
        ToolError: 503 when GreenLake is not configured or failed to start.
    """
    lifespan = ctx.lifespan_context
    token_manager = lifespan.get("greenlake_token_manager")
    config = lifespan.get("config")
    greenlake_cfg = getattr(config, "greenlake", None) if config is not None else None
    if token_manager is None or greenlake_cfg is None:
        raise ToolError(
            {
                "status_code": 503,
                "message": (
                    "GreenLake is not configured or failed to initialize. Provide the GreenLake "
                    "Docker secrets (greenlake_api_base_url, greenlake_client_id, "
                    "greenlake_client_secret, greenlake_workspace_id) and restart the server."
                ),
            }
        )
    return GreenLakeHttpClient(token_manager=token_manager, base_url=greenlake_cfg.api_base_url)


def _body_or_text(response: httpx.Response) -> Any:
    """Parsed JSON body, or {} for an empty 2xx (e.g. 204 No Content)."""
    if not response.content:
        return {}
    try:
        return response.json()
    except (ValueError, _json.JSONDecodeError):
        return {"_raw": response.text}


def _raise_for_status(method: str, path: str, response: httpx.Response) -> None:
    """Convert any non-2xx GreenLake response to a structured ``ToolError``.

    Only ``2xx`` is success. ``httpx`` does not follow redirects by default, so a
    ``3xx`` (regional/proxy routing) must NOT flow through as a fake success — it
    is surfaced as a structured error like any other non-2xx.
    """
    if 200 <= response.status_code < 300:
        return
    try:
        detail: Any = response.json()
    except (ValueError, _json.JSONDecodeError):
        detail = response.text or "Unknown error"
    logger.error("GreenLake API HTTP {} on {} {} — {}", response.status_code, method, path, detail)
    raise ToolError(
        {
            "status_code": response.status_code,
            "message": (_json.dumps(detail) if not isinstance(detail, str) else detail),
        }
    )


def _normalize_location(base_url: str, location: str) -> str:
    """Reduce a ``Location`` header to a base-relative ``/path?query`` for ``client.get()``.

    ``client.get()`` builds ``base_url + endpoint``, so the endpoint must be a
    relative path — never an absolute URL (that would concatenate into a busted
    ``https://hosthttps://other`` URL). Absolute same-origin locations are reduced
    to their ``path?query``; absolute cross-origin locations are rejected with a
    structured ``ToolError`` (we won't blindly follow a Location to a different
    host); relative locations just get a leading slash.
    """
    if location.startswith(("http://", "https://")):
        loc = urlsplit(location)
        base = urlsplit(base_url)
        if (loc.scheme, loc.netloc) != (base.scheme, base.netloc):
            raise ToolError(
                {
                    "status_code": 502,
                    "message": f"GreenLake async Location points to a different host: {location}",
                }
            )
        rel = loc.path + (f"?{loc.query}" if loc.query else "")
        return rel if rel.startswith("/") else f"/{rel}"
    return location if location.startswith("/") else f"/{location}"


async def _poll_async_operation(client: GreenLakeHttpClient, location: str) -> Any:
    """Poll a GreenLake async-operation resource until it reaches a terminal state.

    GreenLake write endpoints return ``202 Accepted`` + a ``Location`` header
    pointing at an async-operation resource. We poll it to a terminal status
    (``SUCCEEDED`` / ``FAILED`` / ``TIMEOUT``) and return the final resource so
    the caller gets the real outcome rather than an opaque 202.
    """
    endpoint = _normalize_location(client.base_url, location)
    for _ in range(_ASYNC_POLL_MAX_ATTEMPTS):
        result = await client.get(endpoint)
        status = (result.get("status") or "").upper() if isinstance(result, dict) else ""
        if status in _ASYNC_TERMINAL:
            return result
        await asyncio.sleep(_ASYNC_POLL_INTERVAL_SECS)
    raise ToolError({"status_code": 504, "message": f"GreenLake async operation did not complete in time: {location}"})


async def greenlake_request(
    ctx: Context,
    method: str,
    path: str,
    *,
    query_params: dict[str, Any] | None = None,
    header_params: dict[str, str] | None = None,
    body: Any | None = None,
) -> Any:
    """Shared transport for the ported GreenLake tools (mirrors upstream's ``greenlake_request``).

    Performs an authenticated request, raising a structured ``ToolError`` on
    non-2xx. For write endpoints that return ``202 Accepted`` + a ``Location``
    header, it auto-polls the async-operation to its terminal state and returns
    the final resource (so an operator sees the real result, not a bare 202).
    Reads return the parsed JSON body.
    """
    client = get_greenlake_client(ctx)
    try:
        response = await client.request_raw(method, path, params=query_params, headers=header_params, json_body=body)
        if response.status_code == 202:
            location = response.headers.get("location") or response.headers.get("Location")
            if location:
                return await _poll_async_operation(client, location)
            return _body_or_text(response)
        _raise_for_status(method, path, response)
        return _body_or_text(response)
    except ToolError:
        raise
    except Exception as exc:
        raise ToolError({"status_code": 502, "message": f"GreenLake {method} {path} failed: {exc}"}) from exc
    finally:
        await client.close()
