#!/bin/bash

if [ -f "/venv/bin/activate" ]; then
    source /venv/bin/activate
fi
alembic upgrade head

if [ "${ENTRYPOINT}" = "server" ]; then
    python -m reflector.app
elif [ "${ENTRYPOINT}" = "worker" ]; then
    celery -A reflector.worker.app worker --loglevel=info
else
    echo "Unknown command"
fi
