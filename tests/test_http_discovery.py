from starlette.testclient import TestClient

from eventor_mcp.config import Settings
from eventor_mcp.server import create_mcp


def test_server_card_uses_configured_public_url() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test",
        EVENTOR_MCP_BEARER_TOKEN="",
    )
    mcp = create_mcp(settings, http_auth=False)
    app = mcp.sse_app()
    client = TestClient(app)
    for path in (
        "/.well-known/mcp/server-card",
        "/.well-known/mcp/server-card/",
        "/.well-known/mcp/server-card.json",
    ):
        r = client.get(path)
        assert r.status_code == 200, path
        data = r.json()
        assert data["name"] == "io.github.jonarnes/eventor-mcp"
        sse = next(x for x in data["remotes"] if x["type"] == "sse")
        assert sse["url"] == "https://mcp.example.test/sse"


def test_server_card_shows_bearer_when_token_set() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test",
        EVENTOR_MCP_BEARER_TOKEN="secret",
    )
    mcp = create_mcp(settings, http_auth=False)
    client = TestClient(mcp.sse_app())
    r = client.get("/.well-known/mcp/server-card")
    auth = r.json()["remotes"][0]["authentication"]
    assert auth["required"] is True
    assert "bearer" in auth["schemes"]


def test_oauth_authorization_server_absent_without_bearer() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test",
        EVENTOR_MCP_BEARER_TOKEN="",
    )
    mcp = create_mcp(settings, http_auth=False)
    client = TestClient(mcp.sse_app())
    assert client.get("/.well-known/oauth-authorization-server").status_code == 404


def test_oauth_authorization_server_metadata_when_bearer_set() -> None:
    settings = Settings(
        _env_file=None,
        EVENTOR_MCP_PUBLIC_URL="https://mcp.example.test",
        EVENTOR_MCP_BEARER_TOKEN="secret",
    )
    mcp = create_mcp(settings, http_auth=True)
    client = TestClient(mcp.sse_app())
    r = client.get("/.well-known/oauth-authorization-server")
    assert r.status_code == 200
    data = r.json()
    assert data["issuer"] == "https://mcp.example.test"
    assert data["authorization_endpoint"] == "https://mcp.example.test/authorize"
    assert data["token_endpoint"] == "https://mcp.example.test/token"
    assert data["response_types_supported"] == ["code"]
    opt = client.options("/.well-known/oauth-authorization-server")
    assert opt.status_code == 204
