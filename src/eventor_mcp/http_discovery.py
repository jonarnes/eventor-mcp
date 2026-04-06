"""
HTTP discovery for remote MCP clients (e.g. Mistral): /.well-known/mcp/server-card*.

See SEP-2127 (draft): https://github.com/modelcontextprotocol/modelcontextprotocol/pull/2127
"""

from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from eventor_mcp import __version__
from eventor_mcp.config import Settings

_SERVER_CARD_PATHS = (
    "/.well-known/mcp/server-card",
    "/.well-known/mcp/server-card/",
    "/.well-known/mcp/server-card.json",
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


def register_mcp_discovery_routes(mcp: FastMCP, settings: Settings) -> None:
    """Public metadata for HTTP MCP discovery (not protected by Bearer)."""

    async def server_card(request: Request) -> JSONResponse:
        return JSONResponse(_server_card_body(request, settings))

    for path in _SERVER_CARD_PATHS:
        mcp.custom_route(path, methods=["GET"])(server_card)
