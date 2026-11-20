from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from ipaddress import ip_address
from typing import Any, Awaitable

import typer

from eventor_mcp.config import Settings
from eventor_mcp.logging_config import setup_logging
from eventor_mcp.runtime import get_runtime, init_runtime, reset_runtime
from eventor_mcp.server import create_mcp

log = logging.getLogger(__name__)


def _validate_http_bind(settings: Settings, host: str) -> None:
    if not settings.allow_insecure_http:
        return
    try:
        loopback = ip_address(host).is_loopback
    except ValueError:
        loopback = host == "localhost"
    if not loopback:
        raise ValueError("ALLOW_INSECURE_HTTP may only bind to a loopback address")


def _listen_port(explicit: int | None, *, fallback: int = 8000) -> int:
    """Use --port if given; else Coolify/Heroku-style ``PORT`` env; else ``fallback``."""

    if explicit is not None:
        return explicit
    raw = os.environ.get("PORT")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return fallback


app = typer.Typer(no_args_is_help=True, help="Eventor MCP server and CLI helpers.")
test_app = typer.Typer(help="Quick API checks without running the MCP host.")
cache_app = typer.Typer(help="Cache management.")
app.add_typer(test_app, name="test")
app.add_typer(cache_app, name="cache")


@app.command()
def serve() -> None:
    """Run the MCP server over stdio (default transport)."""

    settings = Settings()
    setup_logging(settings)
    mcp = create_mcp(settings, http_auth=False)
    asyncio.run(_run_server(settings, mcp.run_stdio_async()))


@app.command("serve-sse")
def serve_sse(
    host: str = typer.Option("127.0.0.1", "--host", help="Bind address (use 0.0.0.0 behind Coolify/Traefik)."),
    port: int | None = typer.Option(
        None,
        "--port",
        help="TCP port for HTTP+SSE (default: env PORT, e.g. 80 on Coolify, else 8000).",
    ),
    mount_path: str | None = typer.Option(
        None,
        "--mount-path",
        help="Optional SSE mount path (default follows FastMCP / MCP library).",
    ),
) -> None:
    """
    Run the MCP server over HTTP with SSE (for products that connect via URL, e.g. Mistral Le Chat custom connectors).

    After starting, use the URL shown by the server (typically /sse) in the connector settings. Exposing this
    on a network without extra protection gives callers access to your Eventor API key scope — prefer localhost plus a
    secure tunnel, or a private deployment.
    """

    settings = Settings()
    setup_logging(settings)
    try:
        _validate_http_bind(settings, host)
        mcp = create_mcp(settings, http_auth=True, http_transport="sse")
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e
    listen = _listen_port(port)
    mcp.settings.host = host
    mcp.settings.port = listen
    log.info("Listening for MCP SSE on %s:%s", host, listen)
    if settings.mcp_bearer_token.strip():
        log.info(
            "MCP HTTP Bearer auth enabled; send the same value as Authorization: Bearer in Mistral."
        )
    asyncio.run(_run_server(settings, mcp.run_sse_async(mount_path=mount_path)))


@app.command("serve-http")
def serve_http(
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int | None = typer.Option(
        None,
        "--port",
        help="TCP port (default: env PORT, else 8000).",
    ),
) -> None:
    """Run the MCP server over streamable HTTP (MCP HTTP transport; use if your client docs ask for it)."""

    settings = Settings()
    setup_logging(settings)
    try:
        _validate_http_bind(settings, host)
        mcp = create_mcp(settings, http_auth=True, http_transport="streamable-http")
    except ValueError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(code=1) from e
    listen = _listen_port(port)
    mcp.settings.host = host
    mcp.settings.port = listen
    log.info("Listening for MCP streamable HTTP on %s:%s", host, listen)
    if settings.mcp_bearer_token.strip():
        log.info(
            "MCP HTTP Bearer auth enabled; send the same value as Authorization: Bearer in Mistral."
        )
    asyncio.run(_run_server(settings, mcp.run_streamable_http_async()))


async def _run_server(settings: Settings, server: Awaitable[None]) -> None:
    # Create, use and close HTTP connection pools on the same event loop.
    init_runtime(settings)
    try:
        await server
    finally:
        await _aclose_runtime()


def _json_dump(data: Any) -> None:
    json.dump(data, sys.stdout, ensure_ascii=False, indent=2, default=str)
    sys.stdout.write("\n")


async def _aclose_runtime() -> None:
    try:
        rt = get_runtime()
    except RuntimeError:
        return
    await rt.client.aclose()
    reset_runtime()


@test_app.command("ping")
def test_ping(
    no_cache: bool = typer.Option(False, "--no-cache", help="Bypass response cache for this call."),
) -> None:
    """Call GET /api/organisation/apiKey and print JSON."""

    async def _run() -> None:
        settings = Settings()
        setup_logging(settings)
        init_runtime(settings)
        try:
            client = get_runtime().client
            data = await client.get_xml("/api/organisation/apiKey", use_cache=not no_cache)
            _json_dump(data)
        finally:
            await _aclose_runtime()

    asyncio.run(_run())


@test_app.command("events")
def test_events(
    from_date: str | None = typer.Option(None, "--from-date"),
    to_date: str | None = typer.Option(None, "--to-date"),
    organisation_ids: str | None = typer.Option(None, "--organisation-ids"),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Call GET /api/events with a date filter."""

    async def _run() -> None:
        settings = Settings()
        setup_logging(settings)
        init_runtime(settings)
        try:
            client = get_runtime().client
            params: dict[str, Any] = {
                "fromDate": from_date,
                "toDate": to_date,
                "includeEntryBreaks": False,
                "includeAttributes": False,
            }
            if organisation_ids:
                params["organisationIds"] = organisation_ids
            data = await client.get_xml("/api/events", params, use_cache=not no_cache)
            _json_dump(data)
        finally:
            await _aclose_runtime()

    asyncio.run(_run())


@test_app.command("get")
def test_get(
    path: str = typer.Argument(..., help="Example: /api/events"),
    query_json: str | None = typer.Option(
        None,
        "--query-json",
        help='Optional JSON object of query parameters, e.g. \'{"fromDate":"2025-01-01 00:00:00"}\'',
    ),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Perform an arbitrary GET (parsed XML → JSON). Useful for quick experiments."""

    async def _run() -> None:
        settings = Settings()
        setup_logging(settings)
        init_runtime(settings)
        try:
            params: dict[str, Any] | None = None
            if query_json:
                loaded = json.loads(query_json)
                if not isinstance(loaded, dict):
                    raise typer.BadParameter("--query-json must be a JSON object")
                params = loaded
            client = get_runtime().client
            data = await client.get_xml(path, params, use_cache=not no_cache)
            _json_dump(data)
        finally:
            await _aclose_runtime()

    asyncio.run(_run())


@test_app.command("organisation")
def test_organisation(
    organisation_id: int = typer.Argument(..., help="Organisation id."),
    no_cache: bool = typer.Option(False, "--no-cache"),
) -> None:
    """Call GET /api/organisation/{id}."""

    async def _run() -> None:
        settings = Settings()
        setup_logging(settings)
        init_runtime(settings)
        try:
            client = get_runtime().client
            data = await client.get_xml(
                f"/api/organisation/{organisation_id}",
                use_cache=not no_cache,
            )
            _json_dump(data)
        finally:
            await _aclose_runtime()

    asyncio.run(_run())


@cache_app.command("clear")
def cache_clear() -> None:
    """Clear the in-process response cache (TTL cache)."""

    settings = Settings()
    setup_logging(settings)
    init_runtime(settings)
    try:
        get_runtime().client.clear_cache()
        typer.echo("Cache cleared.")
    finally:
        asyncio.run(_aclose_runtime())


def main() -> None:
    """Entry point for `eventor-mcp` console script."""

    app()


if __name__ == "__main__":
    main()
