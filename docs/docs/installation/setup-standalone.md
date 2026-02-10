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

If env files already exist, the script only updates LLM vars — it won't overwrite your customizations.

### 3. Transcript storage (skip for standalone)

Production uses AWS S3 to persist processed audio. **Not needed for standalone live/WebRTC mode.**

When `TRANSCRIPT_STORAGE_BACKEND` is unset (the default):
- Audio stays on local disk at `DATA_DIR/{transcript_id}/audio.mp3`
- The live pipeline skips the S3 upload step gracefully
- Audio playback endpoint serves directly from disk
- Post-processing (LLM summary, topics, title) works entirely from DB text
- Diarization (speaker ID) is skipped — already disabled in standalone config (`DIARIZATION_ENABLED=false`)

> **Future**: if file upload or audio persistence across restarts is needed, implement a filesystem storage backend (`storage_local.py`) using the existing `Storage` plugin architecture in `reflector/storage/base.py`. No MinIO required.

### 4. Transcription and diarization

Standalone uses `TRANSCRIPT_BACKEND=whisper` for local CPU-based transcription. Diarization is disabled.

> Another developer is working on optimizing the local transcription experience. For now, local Whisper works for short recordings but is slow on CPU.

### 5. Docker services

```bash
docker compose up -d postgres redis server worker beat web
```

All services start in a single command. No Hatchet in standalone mode — LLM processing (summaries, topics, titles) runs via Celery tasks.

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
- Step 3 (transcript storage) — resolved: skip for live-only mode
- Step 4 (transcription/diarization) — in progress by another developer
- Steps 5-7 (Docker, migrations, health) — implemented
- **Unified script**: `scripts/setup-standalone.sh`
