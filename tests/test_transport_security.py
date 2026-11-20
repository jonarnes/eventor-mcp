"""DNS rebinding / Host header validation (FastMCP + EVENTOR_MCP_PUBLIC_URL)."""

import pytest
from starlette.testclient import TestClient

from eventor_mcp.config import Settings
from eventor_mcp.server import create_mcp


def test_sse_accepts_host_matching_public_url() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test",
        EVENTOR_MCP_BEARER_TOKEN="secret",
    )
    mcp = create_mcp(settings, http_auth=True)
    client = TestClient(mcp.sse_app())
    r = client.get("/sse", headers={"Host": "mcp.example.test"})
    assert r.status_code != 421


def test_sse_rejects_host_not_in_allowlist() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test",
        EVENTOR_MCP_BEARER_TOKEN="secret",
    )
    mcp = create_mcp(settings, http_auth=True)
    client = TestClient(mcp.sse_app())
    # Auth runs before connect_sse; with a valid Bearer, invalid Host fails inside SseServerTransport.
    with pytest.raises(ValueError, match="Request validation failed"):
        client.get(
            "/sse",
            headers={"Host": "attacker.example", "Authorization": "Bearer secret"},
        )


def test_sse_accepts_host_with_nonstandard_port_in_public_url() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test:8443",
        EVENTOR_MCP_BEARER_TOKEN="secret",
    )
    mcp = create_mcp(settings, http_auth=True)
    client = TestClient(mcp.sse_app())
    r = client.get("/sse", headers={"Host": "mcp.example.test:8443"})
    assert r.status_code != 421
