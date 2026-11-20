from pathlib import Path
import tempfile

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


@pytest.mark.asyncio
async def test_chatgpt_launcher_from_another_directory():
    root = Path(__file__).resolve().parents[1]
    params = StdioServerParameters(
        command=str(root / "scripts" / "run-local.sh"), cwd=tempfile.gettempdir(),
        env={"EVENTOR_API_KEY": "test-only", "EVENTOR_API_KEY_HEADER": "ApiKey",
             "EVENTOR_BASE_URL": "https://example.test", "LOG_DIR": "",
             "EVENTOR_MCP_BEARER_TOKEN": "", "EVENTOR_MCP_PUBLIC_URL": ""},
    )
    with tempfile.TemporaryFile(mode="w+") as errlog:
        async with stdio_client(params, errlog=errlog) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await session.initialize()
                tools = (await session.list_tools()).tools
                assert len(tools) == 15
                assert all(tool.annotations.readOnlyHint for tool in tools)
                summary = next(t for t in tools if t.name == "eventor_person_results_summary")
                assert summary.inputSchema["required"] == ["person_id"]
                # MCP round trip, including tool error handling; no Eventor request.
                result = await session.call_tool("eventor_person_results_summary", {
                    "person_id": 1, "from_date": "2025-02-01", "to_date": "2025-01-01",
                })
                assert result.isError
                assert "to_date must be" in result.content[0].text
        errlog.seek(0)
        assert "Event loop is closed" not in errlog.read()


@pytest.mark.asyncio
async def test_default_summary_reaches_client_with_valid_dates(monkeypatch):
    from eventor_mcp.config import Settings
    from eventor_mcp.runtime import init_runtime, reset_runtime
    from eventor_mcp.server import create_mcp
    from eventor_mcp.statistics import assert_date_range_allowed
    config = Settings(_env_file=None, STATS_MAX_DATE_RANGE_DAYS=7)
    runtime = init_runtime(config)
    async def get_xml(path, params):
        assert path == "/api/results/person"
        assert_date_range_allowed(params["fromDate"], params["toDate"], max_days=7)
        return {"ResultListList": ""}
    monkeypatch.setattr(runtime.client, "get_xml", get_xml)
    try:
        mcp = create_mcp(config)
        _, result = await mcp.call_tool("eventor_person_results_summary", {"person_id": 1})
        assert result["summary"]["events_included"] == 0
    finally:
        await runtime.client.aclose()
        reset_runtime()
