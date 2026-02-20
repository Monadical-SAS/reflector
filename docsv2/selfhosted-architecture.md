# How the Self-Hosted Setup Works

This document explains the internals of the self-hosted deployment: how the setup script orchestrates everything, how the Docker Compose profiles work, how services communicate, and how configuration flows from flags to running containers.

> For quick-start instructions and flag reference, see [Self-Hosted Production Deployment](selfhosted-production.md).

## Table of Contents

- [Overview](#overview)
- [The Setup Script Step by Step](#the-setup-script-step-by-step)
- [Docker Compose Profile System](#docker-compose-profile-system)
- [Service Architecture](#service-architecture)
- [Configuration Flow](#configuration-flow)
- [Storage Architecture](#storage-architecture)
- [SSL/TLS and Reverse Proxy](#ssltls-and-reverse-proxy)
- [Build vs Pull Workflow](#build-vs-pull-workflow)
- [Background Task Processing](#background-task-processing)
- [Network and Port Layout](#network-and-port-layout)

---

## Overview

The self-hosted deployment runs the entire Reflector platform on a single server using Docker Compose. A single bash script (`scripts/setup-selfhosted.sh`) handles all configuration and orchestration. The key design principles are:

- **One command to deploy** — flags select which features to enable
- **Idempotent** — safe to re-run without losing existing configuration
- **Profile-based composition** — Docker Compose profiles activate optional services
- **No external dependencies required** — with `--garage` and `--ollama-*`, everything runs locally

## The Setup Script Step by Step

The script (`scripts/setup-selfhosted.sh`) runs 7 sequential steps. Here's what each one does and why.

### Step 0: Prerequisites

Validates the environment before doing anything:

- **Docker Compose V2** — checks `docker compose version` output (not the legacy `docker-compose`)
- **Docker daemon** — verifies `docker info` succeeds
- **NVIDIA GPU** — only checked when `--gpu` or `--ollama-gpu` is used; runs `nvidia-smi` to confirm drivers are installed
- **Compose file** — verifies `docker-compose.selfhosted.yml` exists at the expected path

If any check fails, the script exits with a clear error message and remediation steps.

### Step 1: Generate Secrets

Creates cryptographic secrets needed by the backend and frontend:

- **`SECRET_KEY`** — used by the FastAPI server for session signing (64 hex chars via `openssl rand -hex 32`)
- **`NEXTAUTH_SECRET`** — used by Next.js NextAuth for JWT signing

Secrets are only generated if they don't already exist or are still set to the placeholder value `changeme`. This is what makes the script idempotent for secrets.

If `--password` is passed, this step also generates a PBKDF2-SHA256 password hash from the provided password. The hash is computed using Python's stdlib (`hashlib.pbkdf2_hmac`) with 100,000 iterations and a random 16-byte salt, producing a hash in the format `pbkdf2:sha256:100000$<salt_hex>$<hash_hex>`.

### Step 2: Generate `server/.env`

Creates or updates the backend environment file from `server/.env.selfhosted.example`. Sets:

- **Infrastructure** — PostgreSQL URL, Redis host, Celery broker (all pointing to Docker-internal hostnames)
- **Public URLs** — `BASE_URL` and `CORS_ORIGIN` computed from the domain (if `--domain`), IP (if detected on Linux), or `localhost`
- **WebRTC** — `WEBRTC_HOST` set to the server's LAN IP so browsers can reach UDP ICE candidates
- **Specialized models** — always points to `http://transcription:8000` (the Docker network alias shared by GPU and CPU containers)
- **HuggingFace token** — prompts interactively for pyannote model access; writes to root `.env` so Docker Compose can inject it into GPU/CPU containers
- **LLM** — if `--ollama-*` is used, configures `LLM_URL` pointing to the Ollama container. Otherwise, warns that the user needs to configure an external LLM
- **Public mode** — sets `PUBLIC_MODE=true` so the app is accessible without authentication by default
- **Password auth** — if `--password` is passed, sets `AUTH_BACKEND=password`, `PUBLIC_MODE=false`, `ADMIN_EMAIL=admin@localhost`, and `ADMIN_PASSWORD_HASH` (the hash generated in Step 1). The admin user is provisioned in the database on container startup via `runserver.sh`

The script uses `env_set` for each variable, which either updates an existing line or appends a new one. This means re-running the script updates values in-place without duplicating keys.

### Step 3: Generate `www/.env`

Creates or updates the frontend environment file from `www/.env.selfhosted.example`. Sets:

- **`SITE_URL` / `NEXTAUTH_URL` / `API_URL`** — all set to the same public-facing URL (with `https://` if Caddy is enabled)
- **`WEBSOCKET_URL`** — set to `auto`, which tells the frontend to derive the WebSocket URL from the page URL automatically
- **`SERVER_API_URL`** — always `http://server:1250` (Docker-internal, used for server-side rendering)
- **`KV_URL`** — Redis URL for Next.js caching
- **`FEATURE_REQUIRE_LOGIN`** — `false` by default (matches `PUBLIC_MODE=true` on the backend)
- **Password auth** — if `--password` is passed, sets `FEATURE_REQUIRE_LOGIN=true` and `AUTH_PROVIDER=credentials`, which tells the frontend to use a local email/password login form instead of Authentik OAuth

### Step 4: Storage Setup

Branches based on whether `--garage` was passed:

**With `--garage` (local S3):**

1. Generates `data/garage.toml` from a template, injecting a random RPC secret
2. Starts only the Garage container (`docker compose --profile garage up -d garage`)
3. Waits for the Garage admin API to respond on port 3903
4. Assigns the node to a storage layout (1GB capacity, zone `dc1`)
5. Creates the `reflector-media` bucket
6. Creates an access key named `reflector` and grants it read/write on the bucket
7. Writes all S3 credentials (`ENDPOINT_URL`, `BUCKET_NAME`, `REGION`, `ACCESS_KEY_ID`, `SECRET_ACCESS_KEY`) to `server/.env`

The Garage endpoint is `http://garage:3900` (Docker-internal), and the region is set to `garage` (arbitrary, Garage ignores it). The boto3 client uses path-style addressing when an endpoint URL is configured, which is required for S3-compatible services like Garage.

**Without `--garage` (external S3):**

1. Checks `server/.env` for the four required S3 variables
2. If any are missing, prompts interactively for each one
3. Optionally prompts for an endpoint URL (for MinIO, Backblaze B2, etc.)

### Step 5: Caddyfile

Only runs when `--caddy` or `--domain` is used. Generates a Caddy configuration file:

**With `--domain`:** Creates a named site block (`reflector.example.com { ... }`). Caddy automatically provisions a Let's Encrypt certificate for this domain. Requires DNS pointing to the server and ports 80/443 open.

**Without `--domain` (IP access):** Creates a catch-all `:443 { tls internal ... }` block. Caddy generates a self-signed certificate. Browsers will show a security warning.

Both configurations route:
- `/v1/*` and `/health` to the backend (`server:1250`)
- Everything else to the frontend (`web:3000`)

### Step 6: Start Services

1. **Always builds the GPU/CPU model image** — these are never prebuilt because they contain ML model download logic specific to the host's hardware
2. **With `--build`:** Also builds backend (server, worker, beat) and frontend (web) images from source
3. **Without `--build`:** Pulls prebuilt images from the Docker registry (`monadicalsas/reflector-backend:latest`, `monadicalsas/reflector-frontend:latest`)
4. **Starts all services** — `docker compose up -d` with the active profiles
5. **Quick sanity check** — after 3 seconds, checks for any containers that exited immediately

### Step 7: Health Checks

Waits for each service in order, with generous timeouts:

| Service | Check | Timeout | Notes |
|---------|-------|---------|-------|
| GPU/CPU models | `curl http://localhost:8000/docs` | 10 min (120 x 5s) | First start downloads ~1GB of models |
| Ollama | `curl http://localhost:11435/api/tags` | 3 min (60 x 3s) | Then pulls the selected model |
| Server API | `curl http://localhost:1250/health` | 7.5 min (90 x 5s) | First start runs database migrations |
| Frontend | `curl http://localhost:3000` | 1.5 min (30 x 3s) | Next.js build on first start |
| Caddy | `curl -k https://localhost` | Quick check | After other services are up |

If the server container exits during the health check, the script dumps diagnostics (container statuses + logs) before exiting.

After the Ollama health check passes, the script checks if the selected model is already pulled. If not, it runs `ollama pull <model>` inside the container.

---

## Docker Compose Profile System

The compose file (`docker-compose.selfhosted.yml`) uses Docker Compose profiles to make services optional. Only services whose profiles match the active `--profile` flags are started.

### Always-on Services (no profile)

These start regardless of which flags you pass:

| Service | Role | Image |
|---------|------|-------|
| `server` | FastAPI backend, API endpoints, WebRTC | `monadicalsas/reflector-backend:latest` |
| `worker` | Celery worker for background processing | Same image, `ENTRYPOINT=worker` |
| `beat` | Celery beat scheduler for periodic tasks | Same image, `ENTRYPOINT=beat` |
| `web` | Next.js frontend | `monadicalsas/reflector-frontend:latest` |
| `redis` | Message broker + caching | `redis:7.2-alpine` |
| `postgres` | Primary database | `postgres:17-alpine` |

### Profile-Based Services

| Profile | Service | Role |
|---------|---------|------|
| `gpu` | `gpu` | NVIDIA GPU-accelerated transcription/diarization/translation |
| `cpu` | `cpu` | CPU-only transcription/diarization/translation |
| `ollama-gpu` | `ollama` | Local Ollama LLM with GPU |
| `ollama-cpu` | `ollama-cpu` | Local Ollama LLM on CPU |
| `garage` | `garage` | Local S3-compatible object storage |
| `caddy` | `caddy` | Reverse proxy with SSL |

### The "transcription" Alias

Both the `gpu` and `cpu` services define a Docker network alias of `transcription`. This means the backend always connects to `http://transcription:8000` regardless of which profile is active. The alias is defined in the compose file's `networks.default.aliases` section.

---

## Service Architecture

```
                    ┌─────────────┐
  Internet ────────>│    Caddy     │ :80/:443   (profile: caddy)
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
              v            v            │
         ┌─────────┐  ┌─────────┐      │
         │   web   │  │ server  │      │
         │ :3000   │  │ :1250   │      │
         └─────────┘  └────┬────┘      │
                           │            │
                      ┌────┴────┐       │
                      │ worker  │       │
                      │  beat   │       │
                      └────┬────┘       │
                           │            │
            ┌──────────────┼────────────┤
            │              │            │
            v              v            v
      ┌───────────┐  ┌─────────┐  ┌─────────┐
      │transcription│ │postgres │  │  redis  │
      │ (gpu/cpu) │  │ :5432   │  │ :6379   │
      │ :8000     │  └─────────┘  └─────────┘
      └───────────┘
            │
      ┌─────┴─────┐     ┌─────────┐
      │  ollama   │     │ garage  │
      │(optional) │     │(optional│
      │ :11435    │     │  S3)    │
      └───────────┘     └─────────┘
```

### How Services Interact

1. **User request** hits Caddy (if enabled), which routes to `web` (pages) or `server` (API)
2. **`web`** renders pages server-side using `SERVER_API_URL=http://server:1250` and client-side using the public `API_URL`
3. **`server`** handles API requests, file uploads, WebRTC streaming. Dispatches background work to Celery via Redis
4. **`worker`** picks up Celery tasks (transcription pipelines, audio processing). Calls `transcription:8000` for ML inference and uploads results to S3 storage
5. **`beat`** schedules periodic tasks (cleanup, webhook retries) by pushing them onto the Celery queue
6. **`transcription` (gpu/cpu)** runs Whisper/Parakeet (transcription), Pyannote (diarization), and translation models. Stateless HTTP API
7. **`ollama`** provides an OpenAI-compatible API for summarization and topic detection. Called by the worker during post-processing
8. **`garage`** provides S3-compatible storage for audio files and processed results. Accessed by the worker via boto3

---

## Configuration Flow

Environment variables flow through multiple layers. Understanding this prevents confusion when debugging:

```
Flags (--gpu, --garage, etc.)
  │
  ├── setup-selfhosted.sh interprets flags
  │     │
  │     ├── Writes server/.env (backend config)
  │     ├── Writes www/.env (frontend config)
  │     ├── Writes .env (HF_TOKEN for compose interpolation)
  │     └── Writes Caddyfile (proxy routes)
  │
  └── docker-compose.selfhosted.yml reads:
        ├── env_file: ./server/.env   (loaded into server, worker, beat)
        ├── env_file: ./www/.env      (loaded into web)
        ├── .env                      (compose variable interpolation, e.g. ${HF_TOKEN})
        └── environment: {...}        (hardcoded overrides, always win over env_file)
```

### Precedence Rules

Docker Compose `environment:` keys **always override** `env_file:` values. This is by design — the compose file hardcodes infrastructure values that must be correct inside the Docker network (like `DATABASE_URL=postgresql+asyncpg://...@postgres:5432/...`) regardless of what's in `server/.env`.

The `server/.env` file is still useful for:
- Values not overridden in the compose file (LLM config, storage credentials, auth settings)
- Running the server outside Docker during development

### The Three `.env` Files

| File | Used By | Contains |
|------|---------|----------|
| `server/.env` | server, worker, beat | Backend config: database, Redis, S3, LLM, auth, public URLs |
| `www/.env` | web | Frontend config: site URL, auth, feature flags |
| `.env` (root) | Docker Compose interpolation | Only `HF_TOKEN` — injected into GPU/CPU container env |

---

## Storage Architecture

All audio files and processing results are stored in S3-compatible object storage. The backend uses boto3 (via aioboto3) with automatic path-style addressing when a custom endpoint URL is configured.

### How Garage Works

Garage is a lightweight, self-hosted S3-compatible storage engine. In this deployment:

- Runs as a single-node cluster with 1GB capacity allocation
- Listens on port 3900 (S3 API) and 3903 (admin API)
- Data persists in Docker volumes (`garage_data`, `garage_meta`)
- Accessed by the worker at `http://garage:3900` (Docker-internal)

The setup script creates:
- A bucket called `reflector-media`
- An access key called `reflector` with read/write permissions on that bucket

### Path-Style vs Virtual-Hosted Addressing

AWS S3 uses virtual-hosted addressing by default (`bucket.s3.amazonaws.com`). S3-compatible services like Garage require path-style addressing (`endpoint/bucket`). The `AwsStorage` class detects this automatically: when `TRANSCRIPT_STORAGE_AWS_ENDPOINT_URL` is set, it configures boto3 with `addressing_style: "path"`.

---

## SSL/TLS and Reverse Proxy

### With `--domain` (Production)

Caddy automatically obtains and renews a Let's Encrypt certificate. Requirements:
- DNS A record pointing to the server
- Ports 80 (HTTP challenge) and 443 (HTTPS) open to the internet

The generated Caddyfile uses the domain as the site address, which triggers Caddy's automatic HTTPS.

### Without `--domain` (Development/LAN)

Caddy generates a self-signed certificate and listens on `:443` as a catch-all. Browsers will show a security warning that must be accepted manually.

### Without `--caddy` (BYO Proxy)

No ports are exposed to the internet. The services listen on `127.0.0.1` only:
- Frontend: `localhost:3000`
- Backend API: `localhost:1250`

You can point your own reverse proxy (nginx, Traefik, etc.) at these ports.

### WebRTC and UDP

The server exposes UDP ports 50000-50100 for WebRTC ICE candidates. The `WEBRTC_HOST` variable tells the server which IP to advertise in ICE candidates — this must be the server's actual IP address (not a domain), because WebRTC uses UDP which doesn't go through the HTTP reverse proxy.

---

## Build vs Pull Workflow

### Default (no `--build` flag)

```
GPU/CPU model image: Always built from source (./gpu/self_hosted/)
Backend image:       Pulled from monadicalsas/reflector-backend:latest
Frontend image:      Pulled from monadicalsas/reflector-frontend:latest
```

The GPU/CPU image is always built because it contains hardware-specific build steps and ML model download logic.

### With `--build`

```
GPU/CPU model image: Built from source (./gpu/self_hosted/)
Backend image:       Built from source (./server/)
Frontend image:      Built from source (./www/)
```

Use `--build` when:
- You've made local code changes
- The prebuilt registry images are outdated
- You want to verify the build works on your hardware

### Rebuilding Individual Services

```bash
# Rebuild just the backend
docker compose -f docker-compose.selfhosted.yml build server worker beat

# Rebuild just the frontend
docker compose -f docker-compose.selfhosted.yml build web

# Rebuild the GPU model container
docker compose -f docker-compose.selfhosted.yml build gpu

# Force a clean rebuild (no cache)
docker compose -f docker-compose.selfhosted.yml build --no-cache server
```

---

## Background Task Processing

### Celery Architecture

The backend uses Celery for all background work, with Redis as the message broker:

- **`worker`** — picks up tasks from the Redis queue and executes them
- **`beat`** — schedules periodic tasks (cron-like) by pushing them onto the queue
- **`Redis`** — acts as both message broker and result backend

### The Audio Processing Pipeline

When a file is uploaded, the worker runs a multi-step pipeline:

```
Upload → Extract Audio → Upload to S3
                           │
                    ┌──────┼──────┐
                    │      │      │
                    v      v      v
              Transcribe  Diarize  Waveform
                    │      │      │
                    └──────┼──────┘
                           │
                       Assemble
                           │
                    ┌──────┼──────┐
                    v      v      v
                Topics  Title  Summaries
                           │
                         Done
```

Transcription, diarization, and waveform generation run in parallel. After assembly, topic detection, title generation, and summarization also run in parallel. Each step calls the appropriate service (transcription container for ML, Ollama/external LLM for text generation, S3 for storage).

### Event Loop Management

Each Celery task runs in its own `asyncio.run()` call, which creates a fresh event loop. The `asynctask` decorator in `server/reflector/asynctask.py` handles:

1. **Database connections** — resets the connection pool before each task (connections from a previous event loop would cause "Future attached to a different loop" errors)
2. **Redis connections** — resets the WebSocket manager singleton so Redis pub/sub reconnects on the current loop
3. **Cleanup** — disconnects the database and clears the context variable in the `finally` block

---

## Network and Port Layout

All services communicate over Docker's default bridge network. Only specific ports are exposed to the host:

| Port | Service | Binding | Purpose |
|------|---------|---------|---------|
| 80 | Caddy | `0.0.0.0:80` | HTTP (redirect to HTTPS / Let's Encrypt challenge) |
| 443 | Caddy | `0.0.0.0:443` | HTTPS (main entry point) |
| 1250 | Server | `127.0.0.1:1250` | Backend API (localhost only) |
| 3000 | Web | `127.0.0.1:3000` | Frontend (localhost only) |
| 3900 | Garage | `0.0.0.0:3900` | S3 API (for admin/debug access) |
| 3903 | Garage | `0.0.0.0:3903` | Garage admin API |
| 8000 | GPU/CPU | `127.0.0.1:8000` | ML model API (localhost only) |
| 11435 | Ollama | `127.0.0.1:11435` | Ollama API (localhost only) |
| 50000-50100/udp | Server | `0.0.0.0:50000-50100` | WebRTC ICE candidates |

Services bound to `127.0.0.1` are only accessible from the host itself (not from the network). Caddy is the only service exposed to the internet on standard HTTP/HTTPS ports.

### Docker-Internal Hostnames

Inside the Docker network, services reach each other by their compose service name:

| Hostname | Resolves To |
|----------|-------------|
| `server` | Backend API container |
| `web` | Frontend container |
| `postgres` | PostgreSQL container |
| `redis` | Redis container |
| `transcription` | GPU or CPU container (network alias) |
| `ollama` / `ollama-cpu` | Ollama container |
| `garage` | Garage S3 container |

---

## Diagnostics and Error Handling

The setup script includes an `ERR` trap that automatically dumps diagnostics when any command fails:

1. Lists all container statuses
2. Shows the last 30 lines of logs for any stopped/exited containers
3. Shows the last 40 lines of the specific failing service

This means if something goes wrong during setup, you'll see the relevant logs immediately without having to run manual debug commands.

### Common Debug Commands

```bash
# Overall status
docker compose -f docker-compose.selfhosted.yml ps

# Logs for a specific service
docker compose -f docker-compose.selfhosted.yml logs server --tail 50
docker compose -f docker-compose.selfhosted.yml logs worker --tail 50

# Check environment inside a container
docker compose -f docker-compose.selfhosted.yml exec server env | grep TRANSCRIPT

# Health check from inside the network
docker compose -f docker-compose.selfhosted.yml exec server curl http://localhost:1250/health

# Check S3 storage connectivity
docker compose -f docker-compose.selfhosted.yml exec server curl http://garage:3900

# Database access
docker compose -f docker-compose.selfhosted.yml exec postgres psql -U reflector -c "SELECT id, status FROM transcript ORDER BY created_at DESC LIMIT 5;"

# List files in server data directory
docker compose -f docker-compose.selfhosted.yml exec server ls -la /app/data/
```
