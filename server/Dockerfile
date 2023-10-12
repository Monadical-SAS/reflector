FROM python:3.11-slim as base

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.3.1

# builder install base dependencies
FROM base AS builder
WORKDIR /tmp
RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv

# install application dependencies
COPY pyproject.toml poetry.lock /tmp
RUN . /venv/bin/activate && poetry config virtualenvs.create false
RUN . /venv/bin/activate && poetry install --only main,aws --no-root --no-interaction --no-ansi

# bootstrap
FROM base AS final
COPY --from=builder /venv /venv
RUN mkdir -p /app
COPY reflector /app/reflector
COPY migrations /app/migrations
COPY alembic.ini runserver.sh /app/
WORKDIR /app
CMD ["./runserver.sh"]
