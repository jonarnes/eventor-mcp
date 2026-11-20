"""Public discovery advertises only the HTTP transport actually being served.

Static Bearer authentication is not an OAuth authorization server. No fictitious
OAuth endpoints or grant types are published.
"""
from __future__ import annotations

from typing import Any, Literal

from mcp.server.fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

from eventor_mcp import __version__
from eventor_mcp.config import Settings


def _server_card_body(
    request: Request, settings: Settings, transport: Literal["sse", "streamable-http"],
) -> dict[str, Any]:
    # Public deployments require an explicit origin. Ignore untrusted forwarded headers.
    base = settings.mcp_public_url.strip().rstrip("/") or "http://127.0.0.1:8000"
    bearer = bool(settings.mcp_bearer_token.strip())
    path = "/sse" if transport == "sse" else "/mcp"
    return {
        "$schema": "https://static.modelcontextprotocol.io/schemas/v1/server-card.schema.json",
        "name": "io.github.jonarnes/eventor-mcp",
        "version": __version__,
        "title": "Eventor",
        "description": "Read-only Norwegian Eventor tools: events, entries, results and organisations.",
        "websiteUrl": "https://github.com/jonarnes/eventor-mcp",
        "remotes": [{
            "type": transport,
            "url": f"{base}{path}",
            "authentication": {"required": bearer, "schemes": ["bearer"] if bearer else []},
        }],
        "capabilities": {"tools": {"listChanged": False}},
    }


def register_mcp_discovery_routes(
    mcp: FastMCP, settings: Settings, *, transport: Literal["sse", "streamable-http"],
) -> None:
    async def server_card(request: Request) -> JSONResponse:
        return JSONResponse(_server_card_body(request, settings, transport))

    for path in ("/.well-known/mcp/server-card", "/.well-known/mcp/server-card/", "/.well-known/mcp/server-card.json"):
        mcp.custom_route(path, methods=["GET"])(server_card)

    async def health(request: Request) -> JSONResponse:
        return JSONResponse({"status": "ok"})

    mcp.custom_route("/health", methods=["GET"])(health)
