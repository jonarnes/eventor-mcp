"""Optional Bearer token auth for HTTP/SSE MCP (e.g. Mistral Le Chat connectors)."""

from __future__ import annotations

import secrets
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from pydantic import AnyHttpUrl

from eventor_mcp.config import Settings


def _constant_time_equal(expected: str, received: str) -> bool:
    if len(expected) != len(received):
        return False
    return secrets.compare_digest(expected.encode("utf-8"), received.encode("utf-8"))


class StaticBearerTokenVerifier:
    """Validates Authorization: Bearer <token> against a configured secret."""

    def __init__(self, expected_token: str) -> None:
        self._expected = expected_token

    async def verify_token(self, token: str) -> AccessToken | None:
        if not token or not self._expected:
            return None
        if not _constant_time_equal(self._expected, token):
            return None
        return AccessToken(token=token, client_id="mcp-connector", scopes=[])


def http_mcp_auth_from_settings(settings: Settings) -> tuple[AuthSettings | None, TokenVerifier | None]:
    """
    If EVENTOR_MCP_BEARER_TOKEN is set, return AuthSettings + verifier for FastMCP HTTP transports.

    FastMCP requires AuthSettings (issuer + resource URLs) when enabling token_verifier; for a shared
    static token these can both point at the public base URL of this MCP server (same URL Mistral uses
    as the connector server URL, without path if that is only the host).
    """

    token = settings.mcp_bearer_token.strip()
    if not token:
        return None, None

    base = settings.mcp_public_url.strip().rstrip("/")
    if not base:
        raise ValueError(
            "EVENTOR_MCP_BEARER_TOKEN is set but EVENTOR_MCP_PUBLIC_URL is empty. "
            "Set the public base URL Mistral uses as the connector server URL "
            "(e.g. http://your-host.sslip.io), without a path unless you use one consistently."
        )

    issuer = AnyHttpUrl(base)
    resource = AnyHttpUrl(base)
    auth = AuthSettings(
        issuer_url=issuer,
        resource_server_url=resource,
        required_scopes=[],
    )
    return auth, StaticBearerTokenVerifier(token)
