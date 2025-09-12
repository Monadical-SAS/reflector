#!/bin/sh
set -e

export PATH="/root/.local/bin:$PATH"
cd /app

# Install Python dependencies at runtime (first run or when FORCE_SYNC=1)
if [ ! -d "/app/.venv" ] || [ "$FORCE_SYNC" = "1" ]; then
  echo "[startup] Installing Python dependencies with uv..."
  uv sync --compile-bytecode --locked
else
  echo "[startup] Using existing virtual environment at /app/.venv"
fi

exec uv run uvicorn main:app --host 0.0.0.0 --port 8000


