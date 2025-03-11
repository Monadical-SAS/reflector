#!/bin/bash

if [ -f "/venv/bin/activate" ]; then
    source /venv/bin/activate
fi

if [ "${ENTRYPOINT}" = "server" ]; then
    alembic upgrade head
    python -m reflector.app
elif [ "${ENTRYPOINT}" = "worker" ]; then
    celery -A reflector.worker.app worker --loglevel=info
elif [ "${ENTRYPOINT}" = "beat" ]; then
    celery -A reflector.worker.app beat --loglevel=info
else
    echo "Unknown command"
fi
