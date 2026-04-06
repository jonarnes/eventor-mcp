import pytest

from eventor_mcp.config import Settings
from eventor_mcp.mcp_bearer_auth import StaticBearerTokenVerifier, http_mcp_auth_from_settings


@pytest.mark.asyncio
async def test_static_verifier_accepts_match() -> None:
    v = StaticBearerTokenVerifier("my-secret-token")
    tok = await v.verify_token("my-secret-token")
    assert tok is not None
    assert tok.client_id == "mcp-connector"


@pytest.mark.asyncio
async def test_static_verifier_rejects_mismatch() -> None:
    v = StaticBearerTokenVerifier("expected")
    assert await v.verify_token("wrong") is None


def test_http_mcp_auth_empty_token_returns_none() -> None:
    s = Settings(
        _env_file=None,
        EVENTOR_MCP_BEARER_TOKEN="",
        EVENTOR_MCP_PUBLIC_URL="",
    )
    a, t = http_mcp_auth_from_settings(s)
    assert a is None and t is None


def test_http_mcp_auth_requires_public_url() -> None:
    s = Settings(
        _env_file=None,
        EVENTOR_MCP_BEARER_TOKEN="secret",
        EVENTOR_MCP_PUBLIC_URL="",
    )
    with pytest.raises(ValueError, match="EVENTOR_MCP_PUBLIC_URL"):
        http_mcp_auth_from_settings(s)


def test_http_mcp_auth_returns_pair() -> None:
    s = Settings(
        _env_file=None,
        EVENTOR_MCP_BEARER_TOKEN="tok",
        EVENTOR_MCP_PUBLIC_URL="http://localhost:8000",
    )
    a, t = http_mcp_auth_from_settings(s)
    assert a is not None and t is not None
