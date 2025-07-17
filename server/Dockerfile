FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

# builder install base dependencies
WORKDIR /tmp
RUN apt-get update && apt-get install -y curl && apt-get clean
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"

# install application dependencies
RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml uv.lock /app/
RUN touch README.md && env uv sync --compile-bytecode --locked

# pre-download nltk packages
RUN uv run python -c "import nltk; nltk.download('punkt_tab'); nltk.download('averaged_perceptron_tagger_eng')"

# bootstrap
COPY alembic.ini runserver.sh /app/
COPY images /app/images
COPY migrations /app/migrations
COPY reflector /app/reflector
WORKDIR /app

CMD ["./runserver.sh"]
