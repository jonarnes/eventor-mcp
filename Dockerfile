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
# Coolify often sets PORT=80; override Traefik loadbalancer.server.port to match this port.
EXPOSE 8000
CMD ["sh", "-c", "exec eventor-mcp serve-sse --host 0.0.0.0 --port ${PORT:-8000}"]
