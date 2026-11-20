# Eventor MCP

Read-only MCP server for the Norwegian Eventor orienteering API. Its 15 tools
cover organisations, events, classes, entries, starts, results, competitor counts
and a derived person results summary. It never creates, changes or cancels entries.

API reference: https://eventor.orientering.no/api/documentation. The supplied
Eventor XSD is in `docs/`.

## Local ChatGPT setup

See [Eventor lokalt i ChatGPT](docs/CHATGPT_LOCAL.md) for the complete setup.
ChatGPT desktop supports local stdio MCP; see the
[official MCP documentation](https://learn.chatgpt.com/docs/extend/mcp).

```sh
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
# If .env does not exist: copy .env.example to .env and set EVENTOR_API_KEY.
codex mcp add eventor -- /ABSOLUTE/PATH/eventor-mcp/scripts/run-local.sh
.venv/bin/python scripts/check-local.py --live
```

Restart the MCP server in ChatGPT, then use `/mcp` to check it. The launcher finds
`.env` even when ChatGPT starts in another directory. The local process requires
no MCP Bearer token or public URL. For other stdio clients, use the same launcher,
or `eventor-mcp serve` with the project directory as the working directory.

A local configuration does not connect ChatGPT web; that requires a remote
connection or supported tunnel.

## Data and query behavior

- XML attributes are represented as `@name`; text on an attributed element uses
  `#text`. Example: `<CompetitorStatus value="OK"/>` becomes `{"@value":"OK"}`.
  Unattributed leaf values remain strings. Repeated siblings become arrays;
  a single sibling remains an object or string.
- Events, entries and personal starts default to the next 30 days. Personal
  results and summaries default to the previous 365 days. Configured smaller
  date limits shorten these defaults. Specify both dates for another window.
  With one date supplied, the other is derived using the bounded default span.
- Summary statistics use the overall `PersonResult/Result`, retaining event/class
  context and statuses. Per-race results are not counted again. Unranked and
  invalid finishes count as participation, but do not affect placement statistics.
  Responses include `events_available` and `truncated` when the summary is capped.
- Responses exceeding the byte limit fail explicitly; narrow the query. API
  calls are limited by concurrency, a rolling per-minute quota, and a total
  timeout including queueing and response streaming. Cache hits do not consume
  the upstream request quota. Limits apply per server process.
- The cache is bounded by both entries and estimated parsed-data memory. It is
  private to the process, expires automatically and resets on restart.

## Remote HTTP / Coolify

Remote HTTP requires `EVENTOR_MCP_BEARER_TOKEN` and `EVENTOR_MCP_PUBLIC_URL`.
Use a separate random MCP token, not the Eventor API key. The public URL must be
an HTTPS origin such as `https://eventor.example.no`, without a path. Loopback
HTTP is permitted for development.

```sh
eventor-mcp serve-http --host 0.0.0.0 --port 8000
```

Connect to `https://eventor.example.no/mcp` with
`Authorization: Bearer <EVENTOR_MCP_BEARER_TOKEN>`. Streamable HTTP is the image
default. For an SSE client, override the command with
`serve-sse --host 0.0.0.0`; its endpoint is `/sse`.

1. Build using `Dockerfile`, inject secrets through Coolify, and set the public
   URL to the external HTTPS origin. The image runs as an unprivileged user.
2. Configure Traefik's service port to match `PORT` (default 8000). Use an
   unprivileged port, and terminate TLS at the proxy.
3. Configure a health check on `GET /health` at the container port. This is a
   process liveness endpoint and makes no Eventor request. Use `test ping` for
   an explicit upstream check.
4. `/.well-known/mcp/server-card` advertises only the selected HTTP transport.
   Authentication is a static Bearer token; interactive OAuth endpoints and
   authorization grants are not advertised or implemented. Use a client that
   supports preconfigured Bearer authentication.
5. Do not use the supplied stdio Compose service as a Coolify HTTP service:
   its `command: ["serve"]` intentionally starts a local stdio process.

HTTP startup fails when credentials or origin are missing. Host/Origin validation
remains enabled. For explicitly unauthenticated **loopback development only**:

```sh
ALLOW_INSECURE_HTTP=true EVENTOR_MCP_BEARER_TOKEN= EVENTOR_MCP_PUBLIC_URL= \
  eventor-mcp serve-http --host 127.0.0.1
```

This opt-in cannot bind to `0.0.0.0` or another non-loopback address through the CLI.
Discovery and `/health` are public; MCP requests require the configured token.
Mounting the service below a URL prefix is not supported by public discovery;
use a dedicated hostname with the standard endpoint paths.

## Configuration

See [.env.example](.env.example) for all settings. Key resource defaults:

| Setting | Default | Purpose |
| --- | ---: | --- |
| `API_MAX_DATE_RANGE_DAYS` | 730 | Maximum search date span |
| `API_MAX_RESPONSE_BYTES` | 4000000 | Maximum decoded upstream XML bytes |
| `API_MAX_CONCURRENT_REQUESTS` | 4 | Simultaneous upstream requests |
| `API_REQUESTS_PER_MINUTE` | 60 | Upstream requests per rolling minute |
| `EVENTOR_TIMEOUT_SECONDS` | 30 | Total upstream operation timeout |
| `CACHE_MAX_BYTES` | 32000000 | Estimated parsed-data cache budget |
| `CACHE_MAX_ENTRIES` | 256 | Cache entry count limit |
| `CACHE_TTL_SECONDS` | 300 | Cache freshness interval |
| `STATS_MAX_DATE_RANGE_DAYS` | 730 | Additional summary date limit |
| `STATS_MAX_EVENTS_IN_SUMMARY` | 500 | Summary output row limit |

ID-list parameters accept at most 100 positive comma-separated IDs; `top` accepts
1–1000. Summaries apply the smaller of the general and summary date limits.
Full upstream responses are bounded before parsing; the summary row limit only
controls the output, not the upstream query size.

Logs go to stderr and optionally rotating files via `LOG_DIR`. Container stdout
and stderr are available in Coolify; file logging is optional. In the Docker
image, use an absolute writable path such as `LOG_DIR=/home/eventor/logs` (a
relative path resolves under the root-owned `/app`). If `LOG_DIR` is not
writable, file logging is skipped with a warning. Never commit
`.env` or API keys. API output can contain personal data: all holders of the MCP
Bearer token share the Eventor organisation key's read permissions.

## CLI and tests

```sh
eventor-mcp test ping
eventor-mcp test events --from-date '2026-01-01' --to-date '2026-01-31'
eventor-mcp test organisation 12345
eventor-mcp test get /api/events --query-json '{"fromDate":"2026-01-01","toDate":"2026-01-31"}'
.venv/bin/python -m pytest -q
```

`--no-cache` bypasses the response cache on CLI test commands. The standalone
`cache clear` command only clears its own short-lived process; it cannot flush
an already running MCP server. Restart that server to clear its cache.

The tests cover schema-shaped XML, summary context and statuses, date boundaries,
authentication, discovery, resource limits, and a real stdio MCP subprocess
handshake/tool call. Tests use mocked Eventor data and do not require live keys.
`check-local.py --live` is a separate opt-in integration check.

## License

MIT — see [LICENSE](LICENSE).
