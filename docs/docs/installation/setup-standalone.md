---
sidebar_position: 2
title: Standalone Local Setup
---

# Standalone Local Setup

**The goal**: a clueless user clones the repo, runs one script, and has a working Reflector instance locally. No cloud accounts, no API keys, no manual env file editing.

```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector
./scripts/setup-standalone.sh
```

The script is idempotent — safe to re-run at any time. It detects what's already set up and skips completed steps.

## Prerequisites

- Docker / OrbStack / Docker Desktop (any)
- Mac (Apple Silicon) or Linux
- 16GB+ RAM (32GB recommended for 14B LLM models)
- **Mac only**: [Ollama](https://ollama.com/download) installed (`brew install ollama`)

## What the script does

### 1. LLM inference via Ollama

**Mac**: starts Ollama natively (Metal GPU acceleration). Pulls the LLM model. Docker containers reach it via `host.docker.internal:11434`.

**Linux**: starts containerized Ollama via `docker-compose.standalone.yml` profile (`ollama-gpu` with NVIDIA, `ollama-cpu` without). Pulls model inside the container.

### 2. Environment files

Generates `server/.env` and `www/.env.local` with standalone defaults:

**`server/.env`** — key settings:

| Variable | Value | Why |
|----------|-------|-----|
| `DATABASE_URL` | `postgresql+asyncpg://...@postgres:5432/reflector` | Docker-internal hostname |
| `REDIS_HOST` | `redis` | Docker-internal hostname |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Docker-internal hostname |
| `AUTH_BACKEND` | `none` | No Authentik in standalone |
| `TRANSCRIPT_BACKEND` | `whisper` | Local transcription |
| `DIARIZATION_ENABLED` | `false` | No diarization backend |
| `TRANSLATION_BACKEND` | `passthrough` | No Modal |
| `LLM_URL` | `http://host.docker.internal:11434/v1` (Mac) | Ollama endpoint |

**`www/.env.local`** — key settings:

| Variable | Value |
|----------|-------|
| `API_URL` | `http://localhost:1250` |
| `SERVER_API_URL` | `http://server:1250` |
| `WEBSOCKET_URL` | `ws://localhost:1250` |
| `FEATURE_REQUIRE_LOGIN` | `false` |
| `NEXTAUTH_SECRET` | `standalone-dev-secret-not-for-production` |

If env files already exist (including symlinks from worktree setup), the script resolves symlinks and ensures all standalone-critical vars are set. Existing vars not related to standalone are preserved.

### 3. Object storage (Garage)

Standalone uses [Garage](https://garagehq.deuxfleurs.fr/) — a lightweight S3-compatible object store running in Docker. The setup script starts Garage, initializes the layout, creates a bucket and access key, and writes the credentials to `server/.env`.

**`server/.env`** — storage settings added by the script:

| Variable | Value | Why |
|----------|-------|-----|
| `TRANSCRIPT_STORAGE_BACKEND` | `aws` | Uses the S3-compatible storage driver |
| `TRANSCRIPT_STORAGE_AWS_ENDPOINT_URL` | `http://garage:3900` | Docker-internal Garage S3 API |
| `TRANSCRIPT_STORAGE_AWS_BUCKET_NAME` | `reflector-media` | Created by the script |
| `TRANSCRIPT_STORAGE_AWS_REGION` | `garage` | Must match Garage config |
| `TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID` | *(auto-generated)* | Created by `garage key create` |
| `TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY` | *(auto-generated)* | Created by `garage key create` |

The `TRANSCRIPT_STORAGE_AWS_ENDPOINT_URL` setting enables S3-compatible backends. When set, the storage driver uses path-style addressing and routes all requests to the custom endpoint. When unset (production AWS), behavior is unchanged.

Garage config template lives at `scripts/garage.toml`. The setup script generates `data/garage.toml` (gitignored) with a random RPC secret and mounts it read-only into the container. Single-node, `replication_factor=1`.

> **Note**: Presigned URLs embed the Garage Docker hostname (`http://garage:3900`). This is fine — the server proxies S3 responses to the browser. Modal GPU workers cannot reach internal Garage, but standalone doesn't use Modal.

### 4. Transcription and diarization (NOT YET IMPLEMENTED)

Standalone uses `TRANSCRIPT_BACKEND=whisper` for local CPU-based transcription. Diarization is disabled.

> Another developer is working on optimizing the local transcription experience. For now, local Whisper works for short recordings but is slow on CPU.

### 5. Docker services

```bash
docker compose up -d postgres redis garage server worker beat web
```

All services start in a single command. Garage is already started by step 3 but is included for idempotency. No Hatchet in standalone mode — LLM processing (summaries, topics, titles) runs via Celery tasks.

### 6. Database migrations

Run automatically by the `server` container on startup (`runserver.sh` calls `alembic upgrade head`). No manual step needed.

### 7. Health check

Verifies:
- Server responds at `http://localhost:1250/health`
- Frontend serves at `http://localhost:3000`
- LLM endpoint reachable from inside containers

## Services

| Service | Port | Purpose |
|---------|------|---------|
| `server` | 1250 | FastAPI backend (runs migrations on start) |
| `web` | 3000 | Next.js frontend |
| `postgres` | 5432 | PostgreSQL database |
| `redis` | 6379 | Cache + Celery broker |
| `garage` | 3900, 3903 | S3-compatible object storage (S3 API + admin API) |
| `worker` | — | Celery worker (live pipeline post-processing) |
| `beat` | — | Celery beat (scheduled tasks) |

## What's NOT covered

These require external accounts and infrastructure that can't be scripted:

- **Live meeting rooms** — requires Daily.co account, S3 bucket, IAM roles
- **Authentication** — requires Authentik deployment and OAuth configuration
- **Hatchet workflows** — requires separate Hatchet setup for multitrack processing
- **Production deployment** — see [Deployment Guide](./overview)

## Current status

- Step 1 (Ollama/LLM) — implemented
- Step 2 (environment files) — implemented
- Step 3 (object storage / Garage) — implemented (`docker-compose.standalone.yml` + `setup-standalone.sh`)
- Step 4 (transcription/diarization) — in progress by another developer
- Steps 5-7 (Docker, migrations, health) — implemented
- **Unified script**: `scripts/setup-standalone.sh`
