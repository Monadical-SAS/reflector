FROM python:3.11-slim as base

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.3.1

# install packages needed for base
# RUN apt-get update && apt-get install -y make gettext

# builder
FROM base AS builder
WORKDIR /tmp
# RUN apt-get install -y build-essential libffi-dev zlib1g-dev
COPY pyproject.toml poetry.lock /tmp
RUN pip install "poetry==$POETRY_VERSION"
RUN python -m venv /venv
RUN . /venv/bin/activate && poetry config virtualenvs.create false
RUN . /venv/bin/activate && poetry install --only main --no-root --no-interaction --no-ansi

# bootstrap
FROM base AS final
COPY --from=builder /venv /venv
RUN mkdir -p /app
COPY server.py reflector_dataclasses.py /app/
COPY utils /app/utils
WORKDIR /app
CMD ["/venv/bin/python", "server.py"]
