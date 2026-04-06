import httpx
import pytest

from eventor_mcp.cache import ResponseCache
from eventor_mcp.client import EventorClient
from eventor_mcp.config import Settings


@pytest.mark.asyncio
async def test_get_xml_cache_second_call_skips_http() -> None:
    calls: list[str] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        body = "<EventList><Event><EventId>1</EventId></Event></EventList>"
        return httpx.Response(200, text=body)

    transport = httpx.MockTransport(handler)
    settings = Settings(
        _env_file=None,
        EVENTOR_BASE_URL="https://example.test",
        EVENTOR_API_KEY="",
        EVENTOR_API_KEY_HEADER="ApiKey",
        CACHE_ENABLED=True,
        CACHE_TTL_SECONDS=60,
        CACHE_MAX_ENTRIES=50,
    )

    cache = ResponseCache(settings)
    client = EventorClient(
        settings,
        cache,
        http_client=httpx.AsyncClient(transport=transport, base_url="https://example.test"),
    )
    try:
        a = await client.get_xml("/api/events", {"fromDate": "2025-01-01 00:00:00"})
        b = await client.get_xml("/api/events", {"fromDate": "2025-01-01 00:00:00"})
        assert a == b
        assert len(calls) == 1
    finally:
        await client.aclose()
