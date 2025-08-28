FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

# builder install base dependencies
WORKDIR /tmp
RUN apt-get update && apt-get install -y curl && apt-get clean
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# install application dependencies
RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml uv.lock README.md /app/
RUN uv sync --compile-bytecode --locked

# pre-download nltk packages
RUN uv run python -c "import nltk; nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger_eng')"

# bootstrap
COPY alembic.ini runserver.sh /app/
COPY images /app/images
COPY migrations /app/migrations
COPY reflector /app/reflector
WORKDIR /app

# Create symlink for libgomp if it doesn't exist (for ARM64 compatibility)
RUN if [ "$(uname -m)" = "aarch64" ] && [ ! -f /usr/lib/libgomp.so.1 ]; then \
    LIBGOMP_PATH=$(find /app/.venv/lib -path "*/torch.libs/libgomp*.so.*" 2>/dev/null | head -n1); \
    if [ -n "$LIBGOMP_PATH" ]; then \
    ln -sf "$LIBGOMP_PATH" /usr/lib/libgomp.so.1; \
    fi \
    fi

# Pre-check just to make sure the image will not fail
RUN uv run python -c "import silero_vad.model"

CMD ["./runserver.sh"]
