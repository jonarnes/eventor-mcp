"""
HTTP discovery for remote MCP clients (e.g. Mistral): /.well-known/mcp/server-card*.

When ``EVENTOR_MCP_BEARER_TOKEN`` is set, also exposes RFC 8414 authorization server
metadata at ``/.well-known/oauth-authorization-server`` so clients that probe it
(Mistral uses authlib's ``AuthorizationServerMetadata``) get 200 instead of relying
on fallbacks. This server does not implement interactive OAuth; connectors should use
the configured static Bearer token.

See SEP-2127 (draft): https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from eventor_mcp import __version__
from eventor_mcp.config import Settings

_SERVER_CARD_PATHS = (
    "/.well-known/mcp/server-card",
    "/.well-known/mcp/server-card/",
    "/.well-known/mcp/server-card.json",
)

_OAUTH_AUTHORIZATION_SERVER_PATHS = (
    "/.well-known/oauth-authorization-server",
    "/.well-known/oauth-authorization-server/",
)


def _client_visible_base_url(request: Request, settings: Settings) -> str:
    """Origin as clients should call MCP (Traefik / Coolify forwarding)."""

    configured = settings.mcp_public_url.strip().rstrip("/")
    if configured:
        return configured
    scheme = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host")
    if not host:
        return str(request.base_url).rstrip("/")
    return f"{scheme}://{host}".rstrip("/")


def _server_card_body(request: Request, settings: Settings) -> dict[str, Any]:
    base = _client_visible_base_url(request, settings)
    bearer = bool(settings.mcp_bearer_token.strip())
    auth = (
        {"required": True, "schemes": ["bearer"]}
        if bearer
        else {"required": False, "schemes": []}
    )
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
        "name": "io.github.jonarnes/eventor-mcp",
        "version": __version__,
        "title": "Eventor",
        "description": (
            "Read-only MCP tools for the Norwegian Eventor orienteering API "
            "(events, entries, results, organisations)."
        ),
        "websiteUrl": "https://github.com/jonarnes/eventor-mcp",
        "remotes": [
            {
                "type": "sse",
                "url": f"{base}/sse",
                "supportedProtocolVersions": ["2025-03-12", "2025-06-15"],
                "authentication": auth,
            },
            {
                "type": "streamable-http",
                "url": f"{base}/mcp",
                "supportedProtocolVersions": ["2025-03-12", "2025-06-15"],
                "authentication": auth,
            },
        ],
        "capabilities": {
            "tools": {"listChanged": False},
        },
    }


def _oauth_authorization_server_metadata_body(
    request: Request, settings: Settings
) -> dict[str, Any]:
    """
    Minimal RFC 8414 document that satisfies authlib's AuthorizationServerMetadata.validate().

    Endpoints under the same origin are not implemented; use the pre-shared Bearer token.
    """

    base = _client_visible_base_url(request, settings).rstrip("/")
    return {
        "issuer": base,
        "authorization_endpoint": f"{base}/authorize",
        "token_endpoint": f"{base}/token",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_methods_supported": [
            "client_secret_post",
            "client_secret_basic",
        ],
        "code_challenge_methods_supported": ["S256"],
        "scopes_supported": [],
    }


def _oauth_as_cors_headers() -> dict[str, str]:
    return {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, OPTIONS",
        "Access-Control-Allow-Headers": "*",
    }


def register_mcp_discovery_routes(mcp: FastMCP, settings: Settings) -> None:
    """Public metadata for HTTP MCP discovery (not protected by Bearer)."""

    async def server_card(request: Request) -> JSONResponse:
        return JSONResponse(_server_card_body(request, settings))

    for path in _SERVER_CARD_PATHS:
        mcp.custom_route(path, methods=["GET"])(server_card)

    if not settings.mcp_bearer_token.strip():
        return

    async def oauth_authorization_server(request: Request) -> Response:
        if request.method == "OPTIONS":
            return Response(status_code=204, headers=_oauth_as_cors_headers())
        headers = {
            **_oauth_as_cors_headers(),
            "Cache-Control": "public, max-age=3600",
        }
        return JSONResponse(
            _oauth_authorization_server_metadata_body(request, settings),
            headers=headers,
        )

    for path in _OAUTH_AUTHORIZATION_SERVER_PATHS:
        mcp.custom_route(path, methods=["GET", "OPTIONS"])(oauth_authorization_server)
