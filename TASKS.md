# Standalone Setup — Remaining Tasks

Branch: `local-llm-prd`. Setup doc: `docs/docs/installation/standalone-local-setup.md`.

**Goal**: one script (`scripts/setup-local-dev.sh`) that takes a fresh clone to a working Reflector with no cloud accounts, no API keys, no manual env editing. Live/WebRTC mode only (no file upload, no Daily.co, no Whereby).

**Already done**: Step 1 (Ollama/LLM) in `scripts/setup-local-llm.sh`, Step 3 (storage — skip S3).

**Not our scope**: Step 4 (transcription/diarization) — another developer handles that.

---

## Task 1: Research env defaults for standalone

### Goal

Determine the exact `server/.env` and `www/.env.local` contents for standalone mode. Both files must be generatable by the setup script with zero user input.

### server/.env — what we know

Source of truth for all backend settings: `server/reflector/settings.py` (pydantic BaseSettings, reads from `.env`).

**Vars that MUST be set (no usable default for docker):**

| Variable | Standalone value | Why |
|----------|-----------------|-----|
| `DATABASE_URL` | `postgresql+asyncpg://reflector:reflector@postgres:5432/reflector` | Default is `localhost`, containers need `postgres` hostname |
| `REDIS_HOST` | `redis` | Default is `localhost`, containers need `redis` hostname |
| `CELERY_BROKER_URL` | `redis://redis:6379/1` | Default uses `localhost` |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` | Default uses `localhost` |
| `HATCHET_CLIENT_TOKEN` | *generated at runtime* | Must be extracted from hatchet container after it starts (see below) |

**Vars that MUST be overridden from .env.example defaults:**

| Variable | Standalone value | .env.example has | Why |
|----------|-----------------|------------------|-----|
| `AUTH_BACKEND` | `none` | `jwt` | No Authentik in standalone |
| `TRANSCRIPT_STORAGE_BACKEND` | *(unset/empty)* | `aws` | Skip S3, audio stays local |
| `DIARIZATION_ENABLED` | `false` | `true` (settings.py default) | No diarization backend in standalone |
| `TRANSLATION_BACKEND` | `passthrough` | `modal` (.env.example) | No Modal in standalone. Default in settings.py is already `passthrough`. |

**Vars set by LLM setup (step 1, already handled):**

| Variable | Mac value | Linux GPU value | Linux CPU value |
|----------|-----------|-----------------|-----------------|
| `LLM_URL` | `http://host.docker.internal:11434/v1` | `http://ollama:11434/v1` | `http://ollama-cpu:11434/v1` |
| `LLM_MODEL` | `qwen2.5:14b` | same | same |
| `LLM_API_KEY` | `not-needed` | same | same |

**Vars with safe defaults in settings.py (no override needed):**

- `LLM_CONTEXT_WINDOW` = 16000
- `SECRET_KEY` = `changeme-f02f86fd8b3e4fd892c6043e5a298e21` (fine for local dev)
- `BASE_URL` = `http://localhost:1250`
- `UI_BASE_URL` = `http://localhost:3000`
- `CORS_ORIGIN` = `*`
- `DATA_DIR` = `./data`
- `TRANSCRIPT_BACKEND` = `whisper` (default in settings.py — step 4 developer may change this)
- `HATCHET_CLIENT_TLS_STRATEGY` = `none`
- `PUBLIC_MODE` = `false`

**OPEN QUESTION — Hatchet token chicken-and-egg:**

The `HATCHET_CLIENT_TOKEN` must be generated after the hatchet container starts and creates its DB schema. The current manual process (from `server/README.md`):
```bash
TENANT_ID=$(docker compose exec -T postgres psql -U reflector -d hatchet -t -c \
  "SELECT id FROM \"Tenant\" WHERE slug = 'default';" | tr -d ' \n') && \
TOKEN=$(docker compose exec -T hatchet /hatchet-admin token create \
  --config /config --tenant-id "$TENANT_ID" 2>/dev/null | tr -d '\n') && \
echo "HATCHET_CLIENT_TOKEN=$TOKEN"
```

The setup script needs to:
1. Start postgres + hatchet first
2. Wait for hatchet to be healthy
3. Generate the token
4. Write it to `server/.env`
5. Then start server + workers (which need the token)

**OPEN QUESTION — HATCHET_CLIENT_HOST_PORT and HATCHET_CLIENT_SERVER_URL:**

These are NOT in `settings.py` — they're Hatchet SDK env vars read directly by the SDK. The JWT token embeds `localhost` URLs, but workers inside Docker need `hatchet:7077`. From CLAUDE.md:
```
HATCHET_CLIENT_HOST_PORT=hatchet:7077
HATCHET_CLIENT_SERVER_URL=http://hatchet:8888
HATCHET_CLIENT_TLS_STRATEGY=none
```
These may need to go in `server/.env` too. Verify by checking how hatchet-worker containers connect — they share the same `env_file: ./server/.env` as the server.

### www/.env.local — what we know

The `web` service in `docker-compose.yml` reads `env_file: ./www/.env.local`.

Template: `www/.env.example`. For standalone:

| Variable | Standalone value | Notes |
|----------|-----------------|-------|
| `SITE_URL` | `http://localhost:3000` | |
| `NEXTAUTH_URL` | `http://localhost:3000` | Required by NextAuth |
| `NEXTAUTH_SECRET` | `standalone-dev-secret-not-for-production` | Any string works for dev |
| `API_URL` | `http://localhost:1250` | Browser-side API calls |
| `SERVER_API_URL` | `http://server:1250` | Server-side (SSR) API calls within Docker network |
| `WEBSOCKET_URL` | `ws://localhost:1250` | Browser-side WebSocket |

**Not needed for standalone (no auth):**
- `AUTHENTIK_*` vars — only needed when `AUTH_BACKEND=jwt`
- `FEATURE_REQUIRE_LOGIN` — should be `false` or unset
- `ZULIP_*` — no Zulip integration
- `SENTRY_DSN` — no Sentry

**OPEN QUESTION**: Does the frontend crash if `AUTHENTIK_*` vars are missing? Or does it gracefully skip auth UI when backend reports `AUTH_BACKEND=none`? Check `www/` auth code.

### Deliverable

A concrete list of env vars for each file, with exact values. Resolve all open questions above.

---

## Task 2: Build unified setup script + docker integration

### Goal

Create `scripts/setup-local-dev.sh` that does everything: LLM setup (absorb existing `setup-local-llm.sh`), env file generation, docker services, migrations, health check.

### Depends on

Task 1 (env defaults must be decided first).

### Script structure (from standalone-local-setup.md)

```
setup-local-dev.sh
├── Step 1: LLM/Ollama setup (existing logic from setup-local-llm.sh)
├── Step 2: Generate server/.env and www/.env.local
├── Step 3: (skip — no S3 needed)
├── Step 4: (skip — handled by other developer)
├── Step 5: docker compose up (postgres, redis, hatchet, server, workers, web)
├── Step 6: Wait for services + run migrations
└── Step 7: Health check + print success URLs
```

### Key implementation details

**Idempotency**: Script must be safe to re-run. Each step should check if already done:
- LLM: check if Ollama running + model pulled
- Env files: check if files exist, don't overwrite (or merge carefully)
- Docker: `docker compose up -d` is already idempotent
- Migrations: `alembic upgrade head` is already idempotent
- Health check: always run

**Hatchet token flow** (the tricky part):
1. Generate env files WITHOUT `HATCHET_CLIENT_TOKEN`
2. Start postgres + redis + hatchet
3. Wait for hatchet health (`curl -f http://localhost:8889/api/live`)
4. Generate token via `hatchet-admin` CLI (see Task 1 for command)
5. Append/update `HATCHET_CLIENT_TOKEN=...` in `server/.env`
6. Start server + hatchet-worker-cpu + hatchet-worker-llm + web

**Docker compose invocation**:
- Mac: `docker compose -f docker-compose.yml -f docker-compose.standalone.yml up -d <services>`
- Linux with GPU: add `--profile ollama-gpu`
- Linux without GPU: add `--profile ollama-cpu`
- Services for standalone: `postgres redis hatchet server hatchet-worker-cpu hatchet-worker-llm web`
- Note: `worker` (Celery) and `beat` may not be needed for standalone live mode — verify if live pipeline uses Celery or only Hatchet

**Migrations**: `docker compose exec server uv run alembic upgrade head` — must wait for server container to be ready first.

**Health checks**:
- `curl -sf http://localhost:1250/health` (server `/health` endpoint returns `{"status": "healthy"}`)
- `curl -sf http://localhost:3000` (frontend)
- LLM reachability from container: `docker compose exec server curl -sf http://host.docker.internal:11434/v1/models` (Mac) or equivalent

### Files to create/modify

| File | Action |
|------|--------|
| `scripts/setup-local-dev.sh` | Create — unified setup script |
| `scripts/setup-local-llm.sh` | Keep or remove after folding into unified script |
| `docs/docs/installation/standalone-local-setup.md` | Update status section when done |
| `server/.env.example` | May need standalone section/comments |

### Docker compose considerations

Current `docker-compose.yml` services: server, worker, beat, hatchet-worker-cpu, hatchet-worker-llm, redis, web, postgres, hatchet.

Current `docker-compose.standalone.yml` services: ollama (GPU profile), ollama-cpu (CPU profile).

**OPEN QUESTION**: Does the live pipeline (WebRTC recording) use Celery tasks or Hatchet workflows? If only Hatchet, we can skip `worker` and `beat` services. Check `server/reflector/pipelines/main_live_pipeline.py` — it currently uses Celery chains/chords for post-processing. So `worker` IS needed for live mode.

Update: Looking at `main_live_pipeline.py`, the live pipeline dispatches Celery tasks via `chain()` and `chord()` (lines ~780-810). So both `worker` (Celery) and hatchet workers are needed. `beat` is for cron jobs (cleanup, polling) — probably not critical for standalone demo but harmless to include.

### Final service list for standalone

```
postgres redis hatchet server worker hatchet-worker-cpu hatchet-worker-llm web
```

Plus on Linux: `ollama` or `ollama-cpu` via profile.

---

## Reference: key file locations

| File | Purpose |
|------|---------|
| `server/reflector/settings.py` | All backend env vars with defaults |
| `server/.env.example` | Current env template (production-oriented) |
| `www/.env.example` | Frontend env template |
| `docker-compose.yml` | Main services definition |
| `docker-compose.standalone.yml` | Ollama services for standalone |
| `scripts/setup-local-llm.sh` | Existing LLM setup script |
| `docs/docs/installation/standalone-local-setup.md` | Setup documentation |
| `server/README.md:56-84` | Hatchet token generation commands |
| `server/reflector/hatchet/client.py` | Hatchet client (requires HATCHET_CLIENT_TOKEN) |
| `server/reflector/storage/__init__.py` | Storage factory (skipped when TRANSCRIPT_STORAGE_BACKEND unset) |
| `server/reflector/pipelines/main_live_pipeline.py` | Live pipeline (uses Celery chains for post-processing) |
| `server/reflector/app.py:72-74` | Health endpoint (`GET /health` returns `{"status": "healthy"}`) |
| `server/docker/init-hatchet-db.sql` | Creates `hatchet` DB on postgres init |
