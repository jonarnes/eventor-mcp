from __future__ import annotations

import hashlib
import json
import sys
from typing import Any

from cachetools import TTLCache

from eventor_mcp.config import Settings


def cache_key(method: str, path: str, params: dict[str, Any] | None) -> str:
    """Stable key for HTTP GET cache entries."""

    params = params or {}
    stable = json.dumps(sorted(params.items()), sort_keys=True, default=str)
    raw = f"{method}:{path}:{stable}".encode()
    return hashlib.sha256(raw).hexdigest()


class ResponseCache:
    """TTL cache for parsed API responses (dict / list structures)."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.cache_enabled and settings.cache_ttl_seconds > 0
        ttl = float(settings.cache_ttl_seconds) if self._enabled else 0.0
        maxsize = settings.cache_max_entries if self._enabled else 1
        self._max_entries = maxsize
        self._store: TTLCache[str, Any] = TTLCache(
            maxsize=settings.cache_max_bytes, ttl=ttl, getsizeof=_memory_size,
        )

    def get(self, key: str) -> Any | None:
        if not self._enabled:
            return None
        return self._store.get(key)

    def set(self, key: str, value: Any) -> None:
        if not self._enabled:
            return
        if _memory_size(value) > self._store.maxsize:
            return  # An oversized response remains usable, but is never cached.
        if key not in self._store:
            while len(self._store) >= self._max_entries:
                self._store.popitem()
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()


def _memory_size(value: Any) -> int:
    """Account for parsed dictionaries, lists, keys and strings, once per object."""
    seen: set[int] = set()

    def size(obj: Any) -> int:
        if id(obj) in seen:
            return 0
        seen.add(id(obj))
        total = sys.getsizeof(obj)
        if isinstance(obj, dict):
            total += sum(size(k) + size(v) for k, v in obj.items())
        elif isinstance(obj, (list, tuple)):
            total += sum(size(item) for item in obj)
        return total

    return size(value)
