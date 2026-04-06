FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

ENTRYPOINT ["eventor-mcp"]

# HTTP+SSE for reverse proxies (Coolify, Traefik). Stdio MCP is not usable behind HTTP routing.
# Do not use shell-form CMD: ENTRYPOINT is eventor-mcp, so "sh" would be parsed as a Typer subcommand.
# Listen port: env PORT (Coolify often sets 80); default 8000 is applied in Python if PORT is unset.
EXPOSE 8000
CMD ["serve-sse", "--host", "0.0.0.0"]
