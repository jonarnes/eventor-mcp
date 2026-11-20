from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any

import httpx

from eventor_mcp.cache import ResponseCache, cache_key
from eventor_mcp.config import Settings
from eventor_mcp.xml_parse import parse_eventor_xml
from eventor_mcp.statistics import resolve_date_range

log = logging.getLogger(__name__)


class EventorClient:
    """
    Async HTTP client for Eventor with optional GET caching.

    **Read-only:** only ``get`` requests are issued; there is no POST/PUT/PATCH/DELETE path
    (for example Eventor’s ``PUT /api/competitor`` is intentionally not implemented).
    """

    def __init__(
        self,
        settings: Settings,
        cache: ResponseCache,
        *,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._settings = settings
        self._cache = cache
        self._semaphore = asyncio.Semaphore(settings.api_max_concurrent_requests)
        self._request_times: deque[float] = deque()
        self._owns_client = http_client is None
        headers: dict[str, str] = {}
        if settings.eventor_api_key:
            headers[settings.eventor_api_key_header] = settings.eventor_api_key
        self._client = http_client or httpx.AsyncClient(
            base_url=settings.eventor_base_url,
            headers=headers,
            timeout=settings.eventor_timeout_seconds,
        )

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def clear_cache(self) -> None:
        self._cache.clear()

    async def get_xml(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        use_cache: bool = True,
    ) -> Any:
        """GET endpoint returning parsed XML as dict/list structures."""

        path = path if path.startswith("/") else f"/{path}"
        params = self._bounded_params(path, params or {})
        params = _normalize_params(params)
        ck = cache_key("GET", path, params)
        if use_cache and self._settings.cache_enabled:
            hit = self._cache.get(ck)
            if hit is not None:
                log.debug("cache hit %s", path)
                return hit

        log.info("GET %s", path)
        try:
            # Includes waiting for capacity and reading the entire response body.
            async with asyncio.timeout(self._settings.eventor_timeout_seconds):
                async with self._semaphore:
                    now = time.monotonic()
                    while self._request_times and self._request_times[0] <= now - 60:
                        self._request_times.popleft()
                    if len(self._request_times) >= self._settings.api_requests_per_minute:
                        raise RuntimeError("Eventor request rate limit reached; retry in one minute")
                    self._request_times.append(now)
                    async with self._client.stream("GET", path, params=params) as r:
                        if r.status_code >= 400:
                            # Do not echo upstream response bodies containing personal data.
                            raise RuntimeError(f"HTTP {r.status_code} for {path}")
                        limit = self._settings.api_max_response_bytes
                        body = bytearray()
                        async for chunk in r.aiter_bytes(chunk_size=65536):
                            if len(body) + len(chunk) > limit:
                                raise RuntimeError(f"Response for {path} exceeds API_MAX_RESPONSE_BYTES ({limit}); narrow the query")
                            body.extend(chunk)
                    parsed = parse_eventor_xml(bytes(body))
        except (httpx.RequestError, TimeoutError) as e:
            raise RuntimeError(f"Request failed or timed out for {path}: {e}") from e

        if use_cache and self._settings.cache_enabled:
            self._cache.set(ck, parsed)
        return parsed

    def _bounded_params(self, path: str, params: dict[str, Any]) -> dict[str, Any]:
        params = dict(params)
        if path in {"/api/events", "/api/entries", "/api/results/person", "/api/starts/person"}:
            start_key, end_key = (("fromEventDate", "toEventDate") if path == "/api/entries" else ("fromDate", "toDate"))
            start, end = params.get(start_key), params.get(end_key)
            if start is None and end is None and path != "/api/results/person":
                start = datetime.now().strftime("%Y-%m-%d")
            start, end = resolve_date_range(
                start, end, max_days=self._settings.api_max_date_range_days,
                default_days=365 if path == "/api/results/person" else 30,
            )
            params[start_key], params[end_key] = start, end
        for key, value in params.items():
            if value is not None and key.endswith("Ids"):
                ids = str(value).split(",")
                if len(ids) > 100 or any(not item.strip().isdigit() or int(item) < 1 for item in ids):
                    raise ValueError(f"{key} must contain at most 100 positive comma-separated IDs")
        if params.get("top") is not None and not 1 <= params["top"] <= 1000:
            raise ValueError("top must be between 1 and 1000")
        return params


def _normalize_params(params: dict[str, Any] | None) -> dict[str, Any]:
    if not params:
        return {}
    out: dict[str, Any] = {}
    for k, v in params.items():
        if v is None:
            continue
        if isinstance(v, bool):
            out[k] = str(v).lower()
        else:
            out[k] = v
    return out
