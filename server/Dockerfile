FROM python:3.13-slim as base

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1

# builder install base dependencies
WORKDIR /tmp
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# install application dependencies
RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml uv.lock /app/

# bootstrap
COPY reflector /app/reflector
COPY migrations /app/migrations
COPY images /app/images
COPY alembic.ini runserver.sh /app/
WORKDIR /app
CMD ["./runserver.sh"]
