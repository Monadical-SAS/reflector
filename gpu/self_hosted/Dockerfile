FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

# patch until nvidia updates the sha1 repo
ADD sequoia.config /etc/crypto-policies/back-ends/sequoia.config

WORKDIR /tmp
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
 --mount=type=cache,target=/var/lib/apt,sharing=locked \
 apt-get update \
 && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    gnupg \
    wget
# Add NVIDIA CUDA repo for Debian 12 (bookworm) and install cuDNN 9 for CUDA 12
ADD https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb /cuda-keyring.deb
RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
 --mount=type=cache,target=/var/lib/apt,sharing=locked \
 dpkg -i /cuda-keyring.deb \
 && rm /cuda-keyring.deb \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    cuda-cudart-12-6 \
    libcublas-12-6 \
    libcudnn9-cuda-12 \
    libcudnn9-dev-cuda-12
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml uv.lock /app/


COPY ./app /app/app
COPY ./main.py /app/
COPY ./runserver.sh /app/

# prevent uv failing with too many open files on big cpus
ENV UV_CONCURRENT_INSTALLS=16

# first install
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --compile-bytecode --locked

EXPOSE 8000

CMD ["sh", "/app/runserver.sh"]


