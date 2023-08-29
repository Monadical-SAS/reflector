#!/bin/bash

source venv/bin/activate
alembic upgrade head
python -m reflector.app
