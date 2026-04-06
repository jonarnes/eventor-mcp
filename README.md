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

**Bearer-autentisering (API Token i Mistral):** Når du bruker *API Token Authentication* med `Authorization` + `Bearer`, sett i `.env`:

- `EVENTOR_MCP_BEARER_TOKEN` — **samme hemmelige verdi** som du legger inn som token/«header value» i Mistral (velg et langt tilfeldig passord; dette er **ikke** Eventor API-nøkkelen).
- `EVENTOR_MCP_PUBLIC_URL` — **samme base-URL** som du skriver inn som *Connector Server URL* i Mistral (f.eks. `http://ditt-navn.sslip.io` eller `https://…`), uten path med mindre du bevisst bruker path overalt.

Deretter `serve-sse` / `serve-http`; serveren krever da `Authorization: Bearer <EVENTOR_MCP_BEARER_TOKEN>` på MCP-endepunktene. `eventor-mcp serve` (stdio) bruker **ikke** denne auth og påvirkes ikke.

Gjør slik:

1. Sett `EVENTOR_MCP_BEARER_TOKEN`, `EVENTOR_MCP_PUBLIC_URL`, `EVENTOR_API_KEY` (og øvrig) i `.env`.

2. Start Eventor-MCP med SSE (eller streamable HTTP hvis koblings-UI ber om det):

   ```bash
   eventor-mcp serve-sse --host 127.0.0.1 --port 8000
   ```

   eller:

   ```bash
   eventor-mcp serve-http --host 127.0.0.1 --port 8000
   ```

   Kjør med `cwd` satt til prosjektmappen (eller sett `EVENTOR_*` i miljøet) slik at `.env` lastes.

3. Gjør serveren **tilgjengelig** der Le Chat kan nå den (tunnel mot `127.0.0.1:8000` om nødvendig). **Ikke** eksponer `0.0.0.0` på åpent internett uten ekstra sikring — kall mot MCP bruker din Eventor-nøkkel.

4. Serveren svarer på **MCP discovery**: `GET /.well-known/mcp/server-card` (og `/server-card/`, `server-card.json`) med en **Server Card** som peker til `/sse` og `/mcp`. Dette matcher det mange klienter (inkl. Mistral) spør etter før tilkobling.

5. I **Le Chat**, legg til en **custom MCP connector** og lim inn basis-URL / MCP-URL slik Mistral beskriver i hjelpesidene (produktet endrer seg; følg deres siste steg):
   - [Configuring a Custom Connector](https://help.mistral.ai/en/articles/393572-configuring-a-custom-connector)
   - [Using my MCP Connectors with le Chat](https://help.mistral.ai/en/articles/393511-using-my-mcp-connectors-with-le-chat)

6. **Alternativ:** Bygg en egen «chat» med [Mistral Agents API + MCP](https://docs.mistral.ai/agents/mcp/) i Python og koble **stdio** mot `eventor-mcp serve` (samme mønster som i Mistral-dokumentasjonen med `StdioServerParameters`).

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

The **image default** is **`serve-sse` on `0.0.0.0`** using **`PORT`** (default `8000`) so it works behind Coolify, Traefik, or similar. Override the command if you need stdio or `serve-http`.

Local **stdio** (Cursor-style) via Compose uses `command: ["serve"]`:

```bash
docker compose up --build
```

Run a one-off CLI check (API key required):

```bash
docker compose run --rm -it eventor-mcp test ping
docker compose run --rm -it eventor-mcp test get /api/events --query-json '{"fromDate":"2025-01-01 00:00:00","toDate":"2025-12-31 23:59:59"}'
```

Mount or inject `EVENTOR_API_KEY` via `env_file` or your orchestrator’s secrets. Log files are written to the named volume `eventor_mcp_logs` when `LOG_DIR=/var/log/eventor-mcp` (set in `docker-compose.yml`).

### Coolify / Traefik

1. **Traefik `loadbalancer.server.port`** must equal the port the **container listens on**. If Coolify sets `PORT=80`, use `loadbalancer.server.port=80`. If you use the image default `PORT=8000`, set Traefik to **8000** (not 80 unless the app binds to 80).
2. The app must run **`serve-sse`** (or **`serve-http`** if Mistral requires it), **not** `serve` (stdio). The default Dockerfile command is already `serve-sse`.
3. **`EVENTOR_MCP_PUBLIC_URL`** in `.env` must match the URL Mistral uses (**including `https://`** if you terminate TLS in Traefik). The GUI may show `http://`, but production often uses HTTPS; keep `.env` and Mistral in sync.
4. In Mistral **API Token** mode, fill **Header value** with the **same secret** as `EVENTOR_MCP_BEARER_TOKEN` (the field is not optional for our server when that env is set).

## Configuration

See `.env.example` for:

- `EVENTOR_BASE_URL`, `EVENTOR_API_KEY`, `EVENTOR_API_KEY_HEADER`
- `EVENTOR_MCP_BEARER_TOKEN`, `EVENTOR_MCP_PUBLIC_URL` (HTTP MCP / Mistral Bearer)
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
