#!/bin/sh
# Resolve the project directory so .env also loads when ChatGPT starts elsewhere.
set -eu
PROJECT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$PROJECT_DIR"
if [ ! -x .venv/bin/python ]; then
    echo 'Missing .venv. Run: python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"' >&2
    exit 1
fi
exec .venv/bin/python -m eventor_mcp serve
