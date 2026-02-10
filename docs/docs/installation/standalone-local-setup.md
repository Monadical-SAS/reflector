---
sidebar_position: 2
title: Standalone Local Setup
---

# Standalone Local Setup

**The goal**: a clueless user clones the repo, runs one script, and has a working Reflector instance locally. No cloud accounts, no API keys, no manual env file editing.

```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector
./scripts/setup-local-dev.sh
```

The script is idempotent — safe to re-run at any time. It detects what's already set up and skips completed steps.

## Prerequisites

- Docker / OrbStack / Docker Desktop (any)
- Mac (Apple Silicon) or Linux
- 16GB+ RAM (32GB recommended for 14B LLM models)

## What the script does

### 1. LLM inference via Ollama (implemented)

**Mac**: starts Ollama natively (Metal GPU acceleration). Pulls the LLM model. Docker containers reach it via `host.docker.internal:11434`.

**Linux**: starts containerized Ollama via `docker-compose.standalone.yml` profile (`ollama-gpu` with NVIDIA, `ollama-cpu` without). Pulls model inside the container.

Configures `server/.env`:
```
LLM_URL=http://host.docker.internal:11434/v1
LLM_MODEL=qwen2.5:14b
LLM_API_KEY=not-needed
```

The current standalone script for this step is `scripts/setup-local-llm.sh`. It will be folded into the unified `setup-local-dev.sh` once the other steps are implemented.


### 2. Environment files

The script would copy `.env` templates if not present and fill defaults suitable for local dev (localhost postgres, redis, no auth, etc.).

> The exact set of env defaults and whether the script patches an existing `.env` or only creates from template has not been decided yet. A follow-up research pass can determine what's safe to auto-fill vs. what needs user input.

### 3. Transcript storage (resolved — skip for standalone)

Production uses AWS S3 to persist processed audio. **Not needed for standalone live/WebRTC mode.**

When `TRANSCRIPT_STORAGE_BACKEND` is unset (the default):
- Audio stays on local disk at `DATA_DIR/{transcript_id}/audio.mp3`
- The live pipeline skips the S3 upload step gracefully
- Audio playback endpoint serves directly from disk
- Post-processing (LLM summary, topics, title) works entirely from DB text
- Diarization (speaker ID) is skipped — already disabled in standalone config (`DIARIZATION_ENABLED=false`)

The script ensures `TRANSCRIPT_STORAGE_BACKEND` is left unset in `server/.env`.

> **Future**: if file upload or audio persistence across restarts is needed, implement a filesystem storage backend (`storage_local.py`) using the existing `Storage` plugin architecture in `reflector/storage/base.py`. No MinIO required.

### 4. Transcription and diarization

Production uses Modal.com (cloud GPU) or self-hosted GPU servers.

> The codebase has a `TRANSCRIPT_BACKEND=whisper` option for local Whisper. Whether this runs acceptably on CPU for short dev recordings, and whether diarization has a local fallback, is unknown. For a minimal local setup, it may be sufficient to skip transcription and only test the LLM pipeline against already-transcribed data.

### 5. Docker services

```bash
docker compose up -d postgres redis server hatchet hatchet-worker-cpu hatchet-worker-llm web
```

Frontend included in compose (`web` service). Everything comes up in one command.

### 6. Database migrations

```bash
docker compose exec server uv run alembic upgrade head
```

Idempotent (alembic tracks applied migrations).

### 7. Health check

Verifies:
- Server responds at `http://localhost:1250/health`
- LLM endpoint reachable from inside containers
- Frontend serves at `http://localhost:3000`

## What's NOT covered

These require external accounts and infrastructure that can't be scripted:

- **Live meeting rooms** — requires Daily.co account, S3 bucket, IAM roles
- **Authentication** — requires Authentik deployment and OAuth configuration
- **Production deployment** — see [Deployment Guide](./overview)

## Current status

- Step 1 (Ollama/LLM) — implemented and tested
- Step 3 (transcript storage) — resolved: skip for live-only mode, no code changes needed
- Steps 2, 4, 5, 6, 7 — need a separate research and implementation pass each
