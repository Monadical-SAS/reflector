#!/bin/bash

if [ "${ENTRYPOINT}" = "server" ]; then
    uv run alembic upgrade head
    # Provision admin user if password auth is configured
    if [ -n "${ADMIN_EMAIL:-}" ] && [ -n "${ADMIN_PASSWORD_HASH:-}" ]; then
        uv run python -m reflector.tools.provision_admin
    fi
    uv run uvicorn reflector.app:app --host 0.0.0.0 --port 1250
elif [ "${ENTRYPOINT}" = "worker" ]; then
    uv run celery -A reflector.worker.app worker --loglevel=info
elif [ "${ENTRYPOINT}" = "beat" ]; then
    uv run celery -A reflector.worker.app beat --loglevel=info
elif [ "${ENTRYPOINT}" = "hatchet-worker-cpu" ]; then
    uv run python -m reflector.hatchet.run_workers_cpu
elif [ "${ENTRYPOINT}" = "hatchet-worker-llm" ]; then
    uv run python -m reflector.hatchet.run_workers_llm
else
    echo "Unknown command"
fi
