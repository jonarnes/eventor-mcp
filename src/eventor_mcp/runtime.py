from __future__ import annotations

from dataclasses import dataclass

from eventor_mcp.cache import ResponseCache
from eventor_mcp.client import EventorClient
from eventor_mcp.config import Settings

_rt: "Runtime | None" = None


@dataclass
class Runtime:
    settings: Settings
    client: EventorClient


def init_runtime(settings: Settings) -> Runtime:
    """Create client + cache and store global runtime."""

    global _rt
    cache = ResponseCache(settings)
    client = EventorClient(settings, cache)
    _rt = Runtime(settings=settings, client=client)
    return _rt


def get_runtime() -> Runtime:
    if _rt is None:
        raise RuntimeError("Runtime not initialized; call init_runtime() first")
    return _rt


def reset_runtime() -> None:
    """Mainly for tests."""

    global _rt
    _rt = None
