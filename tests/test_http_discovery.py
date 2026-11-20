import pytest
from starlette.testclient import TestClient
from eventor_mcp.config import Settings
from eventor_mcp.server import create_mcp


@pytest.mark.parametrize("transport,path,other", [("sse", "/sse", "/mcp"), ("streamable-http", "/mcp", "/sse")])
def test_discovery_advertises_only_active_transport(transport, path, other):
    settings = Settings(_env_file=None, EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test", EVENTOR_MCP_BEARER_TOKEN="secret")
    mcp = create_mcp(settings, http_auth=True, http_transport=transport)
    app = mcp.sse_app() if transport == "sse" else mcp.streamable_http_app()
    with TestClient(app) as client:
        for card_path in ("/.well-known/mcp/server-card", "/.well-known/mcp/server-card/", "/.well-known/mcp/server-card.json"):
            r = client.get(card_path)
            assert r.status_code == 200
            assert r.json()["remotes"] == [{"type": transport, "url": f"https://mcp.example.test{path}",
                                           "authentication": {"required": True, "schemes": ["bearer"]}}]
        assert client.get(other).status_code == 404
        for fake in ("/.well-known/oauth-authorization-server", "/authorize", "/token"):
            assert client.get(fake).status_code == 404
        assert client.get("/health").json() == {"status": "ok"}


def test_insecure_local_discovery_does_not_trust_forwarded_host():
    settings = Settings(_env_file=None, ALLOW_INSECURE_HTTP=True, EVENTOR_MCP_PUBLIC_URL="", EVENTOR_MCP_BEARER_TOKEN="")
    mcp = create_mcp(settings, http_auth=True)
    with TestClient(mcp.streamable_http_app()) as client:
        r = client.get("/.well-known/mcp/server-card", headers={"X-Forwarded-Host": "evil.test"})
        assert r.json()["remotes"][0]["url"] == "http://127.0.0.1:8000/mcp"


def test_streamable_http_authentication_and_initialize():
    settings = Settings(_env_file=None, EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test", EVENTOR_MCP_BEARER_TOKEN="secret")
    mcp = create_mcp(settings, http_auth=True)
    headers = {"Host": "mcp.example.test", "Accept": "application/json, text/event-stream"}
    init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
        "protocolVersion": "2025-11-25", "capabilities": {}, "clientInfo": {"name": "test", "version": "1"},
    }}
    with TestClient(mcp.streamable_http_app()) as client:
        assert client.post("/mcp", headers=headers, json=init).status_code == 401
        assert client.post("/mcp", headers={**headers, "Authorization": "Bearer wrong"}, json=init).status_code == 401
        r = client.post("/mcp", headers={**headers, "Authorization": "Bearer secret"}, json=init)
        assert r.status_code == 200
        assert '"serverInfo"' in r.text
        assert r.headers.get("mcp-session-id")
        assert client.post("/mcp", headers={**headers, "Authorization": "Bearer secret", "Host": "attacker.test"}, json=init).status_code == 421
