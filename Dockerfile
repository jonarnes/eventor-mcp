FROM python:3.13-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir .

RUN useradd --create-home --uid 10001 eventor \
    && install -d -o eventor -g eventor /home/eventor/logs
USER eventor

ENTRYPOINT ["eventor-mcp"]
EXPOSE 8000
# Streamable HTTP behind Coolify/Traefik. PORT defaults to 8000.
CMD ["serve-http", "--host", "0.0.0.0"]
