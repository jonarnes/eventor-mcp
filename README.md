# Eventor MCP

A [Model Context Protocol](https://modelcontextprotocol.io/) server that exposes the Norwegian [Eventor](https://eventor.orientering.no/) HTTP API as tools. Use it from AI assistants (for example Cursor) to look up events, entries, starts, results, organisations, and simple derived summaries.

API reference: [eventor.orientering.no/api/documentation](https://eventor.orientering.no/api/documentation) and the official PDF guide linked from that page.

## Features

- **Read-only toward Eventor:** all calls use **HTTP GET** only. The server does not implement write endpoints (such as `PUT /api/competitor`).
- **MCP tools** for organisations, events, classes, entries, starts, results, and a bounded **person results summary** (statistics-style aggregate over `/api/results/person`).
- **Optional response cache** (TTL + max entries) to reduce repeated calls.
- **CLI helpers** for quick checks without an MCP host (`eventor-mcp test …`).
- **Rotating file logs** (optional) with automatic pruning of old log files.

## Requirements

- Python 3.11+
- An Eventor **API key** issued for your organisation (see the official PDF guide).

## Install

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `EVENTOR_API_KEY`.

## Run (MCP / stdio)

```bash
eventor-mcp serve
```

Or:

```bash
python -m eventor_mcp serve
```

### Cursor

Add an MCP server entry that runs the command above (with your venv’s `eventor-mcp` on `PATH`, or `python -m eventor_mcp serve`). Keep secrets in environment variables or a local env file that is **not** committed (`.env` is gitignored).

### Claude Desktop

1. **Installer** prosjektet lokalt (venv + `pip install -e .`) som under [Install](#install).
2. **Finn konfigurasjonsfilen** for MCP:
   - **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`
3. **Legg inn en MCP-server** (JSON). Anbefalt: sett `cwd` til repo-roten slik at `.env` lastes automatisk — da trenger du ikke lime API-nøkkel inn i JSON.

```json
{
  "mcpServers": {
    "eventor": {
      "command": "/FULL/PATH/TO/eventor-mcp/.venv/bin/eventor-mcp",
      "args": ["serve"],
      "cwd": "/FULL/PATH/TO/eventor-mcp"
    }
  }
}
```

Bytt ut stiene med dine absolutte paths (for eksempel `/Users/jonarnes/tempDev/eventor-mcp`). Alternativt kan du bruke `python` + modul:

```json
{
  "mcpServers": {
    "eventor": {
      "command": "/FULL/PATH/TO/eventor-mcp/.venv/bin/python",
      "args": ["-m", "eventor_mcp", "serve"],
      "cwd": "/FULL/PATH/TO/eventor-mcp"
    }
  }
}
```

Hvis du **ikke** bruker `cwd`, må du sette variabler eksplisitt, for eksempel `"env": { "EVENTOR_API_KEY": "…", "EVENTOR_API_KEY_HEADER": "ApiKey" }`.

4. **Lagre filen og start Claude Desktop på nytt** (helt avslutt appen, ikke bare lukk vinduet).
5. I en samtale: verktøyene skal vises som **eventor_…** (for eksempel `eventor_ping`, `eventor_list_events`). Be Claude bruke dem, eller velg verktøy fra verktøy-/MCP-panelet hvis det finnes i din versjon.

**Feilsøking:** Hvis ingenting dukker opp, åpne **Claude → Developer** (eller loggvisning for MCP) og se etter oppstartsfeil fra `eventor-mcp serve`. Kjør `eventor-mcp test ping` i terminal med samme `cwd` og `.env` for å isolere om problemet er nøkkel/nettverk eller Claude-oppsettet.

### Mistral AI (Le Chat og API)

**Le Chat (nett)** snakker med egne MCP-koblinger over **HTTP** (for eksempel **SSE**), ikke over lokal **stdio**. Du kan derfor ikke bruke `eventor-mcp serve` direkte som med Cursor/Claude Desktop, med mindre Mistral tilbyr en «lokal connector» som dokumentert hos dem.

Gjør slik:

1. Start Eventor-MCP med SSE (eller streamable HTTP hvis koblings-UI ber om det):

   ```bash
   eventor-mcp serve-sse --host 127.0.0.1 --port 8000
   ```

   eller:

   ```bash
   eventor-mcp serve-http --host 127.0.0.1 --port 8000
   ```

   Kjør med `cwd` satt til prosjektmappen (eller sett `EVENTOR_*` i miljøet) slik at `.env` med `EVENTOR_API_KEY` lastes.

2. Gjør serveren **tilgjengelig på HTTPS** der Le Chat kan nå den (for lokal testing: tunnel, f.eks. Cloudflare Tunnel / ngrok, mot `127.0.0.1:8000`). **Ikke** eksponer `0.0.0.0` på åpent internett uten ekstra sikring — kall mot MCP bruker din Eventor-nøkkel.

3. I **Le Chat**, legg til en **custom MCP connector** og lim inn basis-URL / MCP-URL slik Mistral beskriver i hjelpesidene (produktet endrer seg; følg deres siste steg):
   - [Configuring a Custom Connector](https://help.mistral.ai/en/articles/393572-configuring-a-custom-connector)
   - [Using my MCP Connectors with le Chat](https://help.mistral.ai/en/articles/393511-using-my-mcp-connectors-with-le-chat)

4. **Alternativ:** Bygg en egen «chat» med [Mistral Agents API + MCP](https://docs.mistral.ai/agents/mcp/) i Python og koble **stdio** mot `eventor-mcp serve` (samme mønster som i Mistral-dokumentasjonen med `StdioServerParameters`).

## CLI testing

```bash
# Verify API key → organisation
eventor-mcp test ping

# List events in a date range
eventor-mcp test events --from-date "2025-01-01 00:00:00" --to-date "2025-12-31 23:59:59"

# Fetch one organisation
eventor-mcp test organisation 12345

# Bypass cache for a single request
eventor-mcp test ping --no-cache

# Clear in-memory cache (same process only; restarts reset it)
eventor-mcp cache clear

# Arbitrary GET (parsed XML as JSON)
eventor-mcp test get /api/events --query-json '{"fromDate":"2025-01-01 00:00:00","toDate":"2025-12-31 23:59:59"}'
```

## Docker

Build and run the MCP server (stdio; interactive flags are enabled in `docker-compose.yml`):

```bash
docker compose up --build
```

Run a one-off CLI check (API key required):

```bash
docker compose run --rm -it eventor-mcp test ping
docker compose run --rm -it eventor-mcp test get /api/events --query-json '{"fromDate":"2025-01-01 00:00:00","toDate":"2025-12-31 23:59:59"}'
```

Mount or inject `EVENTOR_API_KEY` via `env_file` or your orchestrator’s secrets. Log files are written to the named volume `eventor_mcp_logs` when `LOG_DIR=/var/log/eventor-mcp` (set in `docker-compose.yml`).

## Configuration

See `.env.example` for:

- `EVENTOR_BASE_URL`, `EVENTOR_API_KEY`, `EVENTOR_API_KEY_HEADER`
- `CACHE_ENABLED`, `CACHE_TTL_SECONDS`, `CACHE_MAX_ENTRIES`
- `LOG_DIR`, `LOG_LEVEL`, `LOG_ROTATION_WHEN`, `LOG_BACKUP_COUNT`
- `STATS_MAX_DATE_RANGE_DAYS`, `STATS_MAX_EVENTS_IN_SUMMARY`

## Security

- Never commit API keys. This repository is intended to be **public**; use `.env` locally and CI secrets in automation.
- Tool output can contain **personal data** subject to GDPR; log only minimal metadata (no full response bodies by default in code paths—still treat logs as sensitive if you enable debug).

## Repository

Source: [github.com/jonarnes/eventor-mcp](https://github.com/jonarnes/eventor-mcp). Do not commit `.env` or API keys.

**GitHub Actions:** A workflow template lives in [`scripts/github-actions-ci.yml.example`](scripts/github-actions-ci.yml.example). Copy it to `.github/workflows/ci.yml` and commit (from the GitHub UI if needed). Pushing workflow files via HTTPS requires a Personal Access Token with the **workflow** scope.

## License

MIT — see [LICENSE](LICENSE).
