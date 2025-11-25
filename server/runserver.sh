#!/bin/bash

if [ "${ENTRYPOINT}" = "server" ]; then
    uv run alembic upgrade head
    uv run uvicorn reflector.app:app --host 0.0.0.0 --port 1250
elif [ "${ENTRYPOINT}" = "worker" ]; then
    uv run celery -A reflector.worker.app worker --loglevel=info
elif [ "${ENTRYPOINT}" = "beat" ]; then
    uv run celery -A reflector.worker.app beat --loglevel=info
else
    echo "Unknown command"
fi
