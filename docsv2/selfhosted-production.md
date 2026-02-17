# Self-Hosted Production Deployment

Deploy Reflector on a single server with everything running in Docker. Transcription, diarization, and translation use specialized ML models (Whisper/Parakeet, Pyannote); only summarization and topic detection require an LLM.

## Prerequisites

### Hardware
- **With GPU**: Linux server with NVIDIA GPU (8GB+ VRAM recommended), 16GB+ RAM, 50GB+ disk
- **CPU-only**: 8+ cores, 32GB+ RAM (transcription is slower but works)
- Disk space for ML models (~2GB on first run) + audio storage

### Software
- Docker Engine 24+ with Compose V2
- NVIDIA drivers + `nvidia-container-toolkit` (GPU modes only)
- `curl`, `openssl` (usually pre-installed)

### Accounts & Credentials (depending on options)

**Always recommended:**
- **HuggingFace token** — For downloading pyannote speaker diarization models. Get one at https://huggingface.co/settings/tokens and accept the model licenses:
  - https://huggingface.co/pyannote/speaker-diarization-3.1
  - https://huggingface.co/pyannote/segmentation-3.0
  - The setup script will prompt for this. If skipped, diarization falls back to a public model bundle (may be less reliable).

**LLM for summarization & topic detection (pick one):**
- **With `--ollama-gpu` or `--ollama-cpu`**: Nothing extra — Ollama runs locally and pulls the model automatically
- **Without `--ollama-*`**: An OpenAI-compatible LLM API key and endpoint. Examples:
  - OpenAI: `LLM_URL=https://api.openai.com/v1`, `LLM_API_KEY=sk-...`, `LLM_MODEL=gpt-4o-mini`
  - Anthropic, Together, Groq, or any OpenAI-compatible API
  - A self-managed vLLM or Ollama instance elsewhere on the network

**Object storage (pick one):**
- **With `--garage`**: Nothing extra — Garage (local S3-compatible storage) is auto-configured by the script
- **Without `--garage`**: S3-compatible storage credentials. The script will prompt for these, or you can pre-fill `server/.env`. Options include:
  - **AWS S3**: Access Key ID, Secret Access Key, bucket name, region
  - **MinIO**: Same credentials + `TRANSCRIPT_STORAGE_AWS_ENDPOINT_URL=http://your-minio:9000`
  - **Any S3-compatible provider** (Backblaze B2, Cloudflare R2, DigitalOcean Spaces, etc.): same fields + custom endpoint URL

**Optional add-ons (configure after initial setup):**
- **Daily.co** (live meeting rooms): Requires a Daily.co account (https://www.daily.co/), API key, subdomain, and an AWS S3 bucket + IAM Role for recording storage. See [Enabling Daily.co Live Rooms](#enabling-dailyco-live-rooms) below.
- **Authentik** (user authentication): Requires an Authentik instance with an OAuth2/OIDC application configured for Reflector. See [Enabling Authentication](#enabling-authentication-authentik) below.

## Quick Start

```bash
git clone https://github.com/Monadical-SAS/reflector.git
cd reflector

# GPU + local Ollama LLM + local Garage storage + Caddy SSL:
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --garage --caddy

# CPU-only (same, but slower):
./scripts/setup-selfhosted.sh --cpu --ollama-cpu --garage --caddy
```

That's it. The script generates env files, secrets, starts all containers, waits for health checks, and prints the URL.

## Specialized Models (Required)

Pick `--gpu` or `--cpu`. This determines how **transcription, diarization, and translation** run:

| Flag | What it does | Requires |
|------|-------------|----------|
| `--gpu` | NVIDIA GPU acceleration for ML models | NVIDIA GPU + drivers + `nvidia-container-toolkit` |
| `--cpu` | CPU-only (slower but works without GPU) | 8+ cores, 32GB+ RAM recommended |

## Local LLM (Optional)

Optionally add `--ollama-gpu` or `--ollama-cpu` for a **local Ollama instance** that handles summarization and topic detection. If omitted, configure an external OpenAI-compatible LLM in `server/.env`.

| Flag | What it does | Requires |
|------|-------------|----------|
| `--ollama-gpu` | Local Ollama with NVIDIA GPU acceleration | NVIDIA GPU |
| `--ollama-cpu` | Local Ollama on CPU only | Nothing extra |
| `--llm-model MODEL` | Choose which Ollama model to download (default: `qwen2.5:14b`) | `--ollama-gpu` or `--ollama-cpu` |
| *(omitted)* | User configures external LLM (OpenAI, Anthropic, etc.) | LLM API key |

### Choosing an Ollama model

The default model is `qwen2.5:14b` (~9GB download, good multilingual support and summary quality). Override with `--llm-model`:

```bash
# Default (qwen2.5:14b)
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --garage --caddy

# Mistral — good balance of speed and quality (~4.1GB)
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --llm-model mistral --garage --caddy

# Phi-4 — smaller and faster (~9.1GB)
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --llm-model phi4 --garage --caddy

# Llama 3.3 70B — best quality, needs 48GB+ RAM or GPU VRAM (~43GB)
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --llm-model llama3.3:70b --garage --caddy

# Gemma 2 9B (~5.4GB)
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --llm-model gemma2 --garage --caddy

# DeepSeek R1 8B — reasoning model, verbose but thorough summaries (~4.9GB)
./scripts/setup-selfhosted.sh --gpu --ollama-gpu --llm-model deepseek-r1:8b --garage --caddy
```

Browse all available models at https://ollama.com/library.

### Recommended combinations

- **`--gpu --ollama-gpu`**: Best for servers with NVIDIA GPU. Fully self-contained, no external API keys needed.
- **`--cpu --ollama-cpu`**: No GPU available but want everything self-contained. Slower but works.
- **`--gpu --ollama-cpu`**: GPU for transcription, CPU for LLM. Saves GPU VRAM for ML models.
- **`--gpu`**: Have NVIDIA GPU but prefer a cloud LLM (faster/better summaries with GPT-4, Claude, etc.).
- **`--cpu`**: No GPU, prefer cloud LLM. Slowest transcription but best summary quality.

## Other Optional Flags

| Flag | What it does |
|------|-------------|
| `--garage` | Starts Garage (local S3-compatible storage). Auto-configures bucket, keys, and env vars. |
| `--caddy` | Starts Caddy reverse proxy on ports 80/443 with auto-SSL. |

Without `--garage`, you **must** provide S3-compatible credentials (the script will prompt interactively or you can pre-fill `server/.env`).

Without `--caddy`, no ports are exposed. Point your own reverse proxy at `web:3000` (frontend) and `server:1250` (API).

## What the Script Does

1. **Prerequisites check** — Docker, NVIDIA GPU (if needed), compose file exists
2. **Generate secrets** — `SECRET_KEY`, `NEXTAUTH_SECRET` via `openssl rand`
3. **Generate `server/.env`** — From template, sets infrastructure defaults, configures LLM based on mode
4. **Generate `www/.env`** — Auto-detects server IP, sets URLs
5. **Storage setup** — Either initializes Garage (bucket, keys, permissions) or prompts for external S3 credentials
6. **Caddyfile** — Generates with server IP if on Linux, copies template otherwise
7. **Build & start** — Builds GPU/CPU image from source, starts all containers
8. **Health checks** — Waits for each service, pulls Ollama model if needed, warns about missing LLM config

## Configuration Reference

### Server Environment (`server/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | Auto-set (Docker internal) |
| `REDIS_HOST` | Redis hostname | Auto-set (`redis`) |
| `SECRET_KEY` | App secret | Auto-generated |
| `AUTH_BACKEND` | Authentication method | `none` |
| `TRANSCRIPT_URL` | Specialized model endpoint | `http://transcription:8000` |
| `LLM_URL` | OpenAI-compatible LLM endpoint | Auto-set for Ollama modes |
| `LLM_API_KEY` | LLM API key | `not-needed` for Ollama |
| `LLM_MODEL` | LLM model name | `qwen2.5:14b` for Ollama (override with `--llm-model`) |
| `TRANSCRIPT_STORAGE_BACKEND` | Storage backend | `aws` |
| `TRANSCRIPT_STORAGE_AWS_*` | S3 credentials | Auto-set for Garage |

### Frontend Environment (`www/.env`)

| Variable | Description | Default |
|----------|-------------|---------|
| `SITE_URL` | Public-facing URL | Auto-detected |
| `API_URL` | API URL (browser-side) | Same as SITE_URL |
| `SERVER_API_URL` | API URL (server-side) | `http://server:1250` |
| `NEXTAUTH_SECRET` | Auth secret | Auto-generated |
| `FEATURE_REQUIRE_LOGIN` | Require authentication | `false` |

## Storage Options

### Garage (Recommended for Self-Hosted)

Use `--garage` flag. The script automatically:
- Generates `data/garage.toml` with a random RPC secret
- Starts the Garage container
- Creates the `reflector-media` bucket
- Creates an access key with read/write permissions
- Writes all S3 credentials to `server/.env`

### External S3 (AWS, MinIO, etc.)

Don't use `--garage`. The script will prompt for:
- Access Key ID
- Secret Access Key
- Bucket Name
- Region
- Endpoint URL (for non-AWS like MinIO)

Or pre-fill in `server/.env`:
```env
TRANSCRIPT_STORAGE_BACKEND=aws
TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID=your-key
TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY=your-secret
TRANSCRIPT_STORAGE_AWS_BUCKET_NAME=reflector-media
TRANSCRIPT_STORAGE_AWS_REGION=us-east-1
# For non-AWS S3 (MinIO, etc.):
TRANSCRIPT_STORAGE_AWS_ENDPOINT_URL=http://minio:9000
```

## Enabling Authentication (Authentik)

By default, authentication is disabled (`AUTH_BACKEND=none`, `FEATURE_REQUIRE_LOGIN=false`). To enable:

1. Deploy an Authentik instance (see [Authentik docs](https://goauthentik.io/docs/installation))
2. Create an OAuth2/OIDC application for Reflector
3. Update `server/.env`:
   ```env
   AUTH_BACKEND=jwt
   AUTH_JWT_AUDIENCE=your-client-id
   ```
4. Update `www/.env`:
   ```env
   FEATURE_REQUIRE_LOGIN=true
   AUTHENTIK_ISSUER=https://authentik.example.com/application/o/reflector
   AUTHENTIK_REFRESH_TOKEN_URL=https://authentik.example.com/application/o/token/
   AUTHENTIK_CLIENT_ID=your-client-id
   AUTHENTIK_CLIENT_SECRET=your-client-secret
   ```
5. Restart: `docker compose -f docker-compose.selfhosted.yml down && ./scripts/setup-selfhosted.sh <same-flags>`

## Enabling Daily.co Live Rooms

Daily.co enables real-time meeting rooms with automatic recording and transcription.

1. Create a [Daily.co](https://www.daily.co/) account
2. Add to `server/.env`:
   ```env
   DEFAULT_VIDEO_PLATFORM=daily
   DAILY_API_KEY=your-daily-api-key
   DAILY_SUBDOMAIN=your-subdomain
   DAILY_WEBHOOK_SECRET=your-webhook-secret
   DAILYCO_STORAGE_AWS_BUCKET_NAME=reflector-dailyco
   DAILYCO_STORAGE_AWS_REGION=us-east-1
   DAILYCO_STORAGE_AWS_ROLE_ARN=arn:aws:iam::role/DailyCoAccess
   ```
3. Restart the server: `docker compose -f docker-compose.selfhosted.yml restart server worker`

## Enabling Real Domain with Let's Encrypt

By default, Caddy uses self-signed certificates. For a real domain:

1. Point your domain's DNS to your server's IP
2. Ensure ports 80 and 443 are open
3. Edit `Caddyfile`:
   ```
   reflector.example.com {
       handle /v1/* {
           reverse_proxy server:1250
       }
       handle /health {
           reverse_proxy server:1250
       }
       handle {
           reverse_proxy web:3000
       }
   }
   ```
4. Update `www/.env`:
   ```env
   SITE_URL=https://reflector.example.com
   NEXTAUTH_URL=https://reflector.example.com
   API_URL=https://reflector.example.com
   ```
5. Restart Caddy: `docker compose -f docker-compose.selfhosted.yml restart caddy web`

## Troubleshooting

### Check service status
```bash
docker compose -f docker-compose.selfhosted.yml ps
```

### View logs for a specific service
```bash
docker compose -f docker-compose.selfhosted.yml logs server --tail 50
docker compose -f docker-compose.selfhosted.yml logs gpu --tail 50
docker compose -f docker-compose.selfhosted.yml logs web --tail 50
```

### GPU service taking too long
First start downloads ~1-2GB of ML models. Check progress:
```bash
docker compose -f docker-compose.selfhosted.yml logs gpu -f
```

### Server exits immediately
Usually a database migration issue. Check:
```bash
docker compose -f docker-compose.selfhosted.yml logs server --tail 50
```

### Caddy certificate issues
For self-signed certs, your browser will warn. Click Advanced > Proceed.
For Let's Encrypt, ensure ports 80/443 are open and DNS is pointed correctly.

### Summaries/topics not generating
Check LLM configuration:
```bash
grep LLM_ server/.env
```
If you didn't use `--ollama-gpu` or `--ollama-cpu`, you must set `LLM_URL`, `LLM_API_KEY`, and `LLM_MODEL`.

### Health check from inside containers
```bash
docker compose -f docker-compose.selfhosted.yml exec server curl http://localhost:1250/health
docker compose -f docker-compose.selfhosted.yml exec gpu curl http://localhost:8000/docs
```

## Updating

```bash
# Pull latest images
docker compose -f docker-compose.selfhosted.yml pull

# Rebuild GPU/CPU image (picks up model updates)
docker compose -f docker-compose.selfhosted.yml build gpu  # or cpu

# Restart
docker compose -f docker-compose.selfhosted.yml down
./scripts/setup-selfhosted.sh <same-flags-as-before>
```

The setup script is idempotent — it won't overwrite existing secrets or env vars that are already set.

## Architecture Overview

```
                    ┌─────────┐
  Internet ────────>│  Caddy  │ :80/:443
                    └────┬────┘
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
    │transcription│  │postgres │  │  redis  │
    │(gpu/cpu)  │  │ :5432   │  │ :6379   │
    │ :8000     │  └─────────┘  └─────────┘
    └───────────┘
          │
    ┌─────┴─────┐     ┌─────────┐
    │  ollama   │     │ garage  │
    │ (optional)│     │(optional│
    │ :11434    │     │ S3)     │
    └───────────┘     └─────────┘
```

All services communicate over Docker's internal network. Only Caddy (if enabled) exposes ports to the internet.