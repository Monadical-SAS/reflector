---
sidebar_position: 2
title: Local Development Setup
---

# Local Development Setup

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

**Linux**: starts containerized Ollama via docker-compose profile (`ollama-gpu` with NVIDIA, `ollama-cpu` without). Pulls model inside the container.

Configures `server/.env`:
```
LLM_URL=http://host.docker.internal:11434/v1
LLM_MODEL=qwen2.5:14b
LLM_API_KEY=not-needed
```

The current standalone script for this step is `scripts/setup-local-llm.sh`. It will be folded into the unified `setup-local-dev.sh` once the other steps are implemented.

See [Ollama PRD](../../01_ollama.prd.md) for architecture, why Ollama over Docker Model Runner, and model comparison.

### 2. Environment files

The script would copy `.env` templates if not present and fill defaults suitable for local dev (localhost postgres, redis, no auth, etc.).

> The exact set of env defaults and whether the script patches an existing `.env` or only creates from template has not been decided yet. A follow-up research pass can determine what's safe to auto-fill vs. what needs user input.

### 3. Transcript storage

Production uses AWS S3. Local dev needs an alternative.

> Options include MinIO in docker-compose (S3-compatible, zero config), a filesystem-backed storage backend (if one exists in the codebase), or skipping storage for dev if the pipeline can function without it. This depends on what `TRANSCRIPT_STORAGE_BACKEND` supports beyond `aws` — needs investigation.

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

Step 1 (Ollama/LLM) is implemented and tested. Steps 2-7 need a separate research and implementation pass each.
