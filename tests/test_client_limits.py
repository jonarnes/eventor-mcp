import asyncio

import httpx
import pytest

from eventor_mcp.cache import ResponseCache
from eventor_mcp.client import EventorClient
from eventor_mcp.config import Settings


def settings(**overrides):
    return Settings(_env_file=None, EVENTOR_API_KEY="", **overrides)


async def fetch(handler, config, path="/api/events", params=None):
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test") as http:
        client = EventorClient(config, ResponseCache(config), http_client=http)
        return await client.get_xml(path, params)


@pytest.mark.asyncio
async def test_excessive_date_range_is_rejected_before_http():
    async def handler(request):
        pytest.fail("Must not reach upstream")
    with pytest.raises(ValueError, match="Date range"):
        await fetch(handler, settings(), params={"fromDate": "2000-01-01", "toDate": "2025-01-01"})


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["/api/events", "/api/entries", "/api/results/person", "/api/starts/person"])
async def test_default_requests_have_bounded_valid_dates(path):
    async def handler(request):
        a, b = ("fromEventDate", "toEventDate") if path == "/api/entries" else ("fromDate", "toDate")
        from eventor_mcp.statistics import assert_date_range_allowed
        assert_date_range_allowed(request.url.params[a], request.url.params[b], max_days=7)
        return httpx.Response(200, text="<Root/>")
    await fetch(handler, settings(API_MAX_DATE_RANGE_DAYS=7), path=path)


class ChunkedBody(httpx.AsyncByteStream):
    def __init__(self):
        self.consumed = 0
        self.closed = False

    async def __aiter__(self):
        for _ in range(100):
            self.consumed += 1
            yield b"x" * 65536

    async def aclose(self):
        self.closed = True


@pytest.mark.asyncio
async def test_oversized_body_stops_streaming_and_closes_connection():
    body = ChunkedBody()
    async def handler(request):
        return httpx.Response(200, stream=body)
    with pytest.raises(RuntimeError, match="API_MAX_RESPONSE_BYTES"):
        await fetch(handler, settings(API_MAX_RESPONSE_BYTES=65536))
    assert body.consumed == 2
    assert body.closed


@pytest.mark.asyncio
async def test_concurrency_is_bounded_and_rate_limit_applies_to_cache_misses():
    active = peak = calls = 0
    async def handler(request):
        nonlocal active, peak, calls
        active += 1
        peak = max(peak, active)
        calls += 1
        await asyncio.sleep(0.01)
        active -= 1
        return httpx.Response(200, text="<Root/>")
    config = settings(API_MAX_CONCURRENT_REQUESTS=2, API_REQUESTS_PER_MINUTE=4)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test") as http:
        client = EventorClient(config, ResponseCache(config), http_client=http)
        await asyncio.gather(*(client.get_xml(f"/api/event/{i}") for i in range(4)))
        assert peak == 2
        await client.get_xml("/api/event/0")  # cache hit is still usable
        with pytest.raises(RuntimeError, match="rate limit"):
            await client.get_xml("/api/event/5")
        assert calls == 4


@pytest.mark.asyncio
async def test_rate_limit_recovers_after_window(monkeypatch):
    now = [100.0]
    monkeypatch.setattr("eventor_mcp.client.time.monotonic", lambda: now[0])
    async def handler(request):
        return httpx.Response(200, text="<Root/>")
    config = settings(API_REQUESTS_PER_MINUTE=1, CACHE_ENABLED=False)
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://example.test") as http:
        client = EventorClient(config, ResponseCache(config), http_client=http)
        await client.get_xml("/api/event/1")
        with pytest.raises(RuntimeError, match="rate limit"):
            await client.get_xml("/api/event/1")
        now[0] += 61
        await client.get_xml("/api/event/1")


@pytest.mark.asyncio
async def test_total_request_timeout():
    async def handler(request):
        await asyncio.sleep(1)
        return httpx.Response(200, text="<Root/>")
    with pytest.raises(RuntimeError, match="timed out"):
        await fetch(handler, settings(EVENTOR_TIMEOUT_SECONDS=0.01))


def test_cache_obeys_byte_and_entry_limits():
    config = settings(CACHE_MAX_BYTES=1500, CACHE_MAX_ENTRIES=2)
    cache = ResponseCache(config)
    cache.set("a", {"body": "a" * 500})
    cache.set("b", {"body": "b" * 500})
    assert cache.get("a") is None
    assert cache.get("b") is not None
    cache.set("huge", {"body": "c" * 3000})
    assert cache.get("huge") is None
    cache.set("c", "c")
    cache.set("d", "d")
    assert cache.get("b") is None
    assert cache.get("c") == "c"
    assert cache.get("d") == "d"
