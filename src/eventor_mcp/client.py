from __future__ import annotations

import logging
from typing import Any

import httpx

from eventor_mcp.cache import ResponseCache, cache_key
from eventor_mcp.config import Settings
from eventor_mcp.xml_parse import parse_eventor_xml

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
        params = _normalize_params(params)
        ck = cache_key("GET", path, params)
        if use_cache and self._settings.cache_enabled:
            hit = self._cache.get(ck)
            if hit is not None:
                log.debug("cache hit %s", path)
                return hit

        log.info("GET %s", path)
        try:
            r = await self._client.get(path, params=params)
            r.raise_for_status()
        except httpx.HTTPStatusError as e:
            body = (e.response.text or "")[:500]
            if e.response.status_code == 403 and "<title>403" in body and not self._settings.eventor_api_key.strip():
                raise RuntimeError(
                    f"HTTP 403 for {path}. The API key may be missing: set EVENTOR_API_KEY in .env "
                    "(the secret from Eventor). EVENTOR_API_KEY_HEADER should be the header *name* "
                    "(usually ApiKey), not the key value."
                ) from e
            raise RuntimeError(f"HTTP {e.response.status_code} for {path}: {body}") from e
        except httpx.RequestError as e:
            raise RuntimeError(f"Request failed for {path}: {e}") from e

        parsed = parse_eventor_xml(r.text)
        if use_cache and self._settings.cache_enabled:
            self._cache.set(ck, parsed)
        return parsed


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
