#!/bin/bash

if [ "${ENTRYPOINT}" = "server" ]; then
    uv run alembic upgrade head
    uv run -m reflector.app
elif [ "${ENTRYPOINT}" = "worker" ]; then
    uv run celery -A reflector.worker.app worker --loglevel=info
elif [ "${ENTRYPOINT}" = "beat" ]; then
    uv run celery -A reflector.worker.app beat --loglevel=info
else
    echo "Unknown command"
fi
