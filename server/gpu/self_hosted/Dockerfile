FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_NO_CACHE=1

WORKDIR /tmp
RUN apt-get update \
 && apt-get install -y \
    ffmpeg \
    curl \
    ca-certificates \
    gnupg \
    wget \
 && apt-get clean
# Add NVIDIA CUDA repo for Debian 12 (bookworm) and install cuDNN 9 for CUDA 12
ADD https://developer.download.nvidia.com/compute/cuda/repos/debian12/x86_64/cuda-keyring_1.1-1_all.deb /cuda-keyring.deb
RUN dpkg -i /cuda-keyring.deb \
 && rm /cuda-keyring.deb \
 && apt-get update \
 && apt-get install -y --no-install-recommends \
    cuda-cudart-12-6 \
    libcublas-12-6 \
    libcudnn9-cuda-12 \
    libcudnn9-dev-cuda-12 \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh
ENV PATH="/root/.local/bin/:$PATH"
ENV LD_LIBRARY_PATH="/usr/local/cuda/lib64:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"

RUN mkdir -p /app
WORKDIR /app
COPY pyproject.toml uv.lock /app/


COPY ./app /app/app
COPY ./main.py /app/
COPY ./start.sh /app/

EXPOSE 8000

CMD ["sh", "/app/start.sh"]


