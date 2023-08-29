#!/bin/bash

if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi
alembic upgrade head
python -m reflector.app
