---
sidebar_position: 1
title: Deployment Guide
---

# Deployment Guide

This guide walks you through deploying Reflector from scratch. Follow these steps in order.

## What You'll Set Up

```mermaid
flowchart LR
    User --> Caddy["Caddy (auto-SSL)"]
    Caddy --> Frontend["Frontend (Next.js)"]
    Caddy --> Backend["Backend (FastAPI)"]
    Backend --> PostgreSQL
    Backend --> Redis
    Backend --> Workers["Celery Workers"]
    Workers --> PostgreSQL
    Workers --> Redis
    Workers --> GPU["GPU Processing<br/>(Modal.com OR Self-hosted)"]
```

## Prerequisites

Before starting, you need:

- [ ] **Production server** - Ubuntu 22.04+, 4+ cores, 8GB+ RAM, public IP
- [ ] **Two domain names** - e.g., `app.example.com` (frontend) and `api.example.com` (backend)
- [ ] **GPU processing** - Choose one:
  - Modal.com account (free tier at https://modal.com), OR
  - GPU server with NVIDIA GPU (8GB+ VRAM)
- [ ] **HuggingFace account** - Free at https://huggingface.co
- [ ] **OpenAI API key** - For summaries and topic detection at https://platform.openai.com/account/api-keys

### Optional (for live meeting rooms)

- [ ] **Daily.co account** - Free tier at https://dashboard.daily.co
- [ ] **AWS S3 bucket** - For Daily.co recording storage

---

## Step 1: Configure DNS

**Location: Your domain registrar / DNS provider**

Create A records pointing to your server:
```
Type: A    Name: app    Value: <your-server-ip>
Type: A    Name: api    Value: <your-server-ip>
```

Verify propagation (wait a few minutes):
```bash
dig app.example.com +short
dig api.example.com +short
# Both should return your server IP
```

---

## Step 2: Deploy GPU Processing

Reflector requires GPU processing for transcription (Whisper) and speaker diarization (Pyannote). Choose one option:

| | **Modal.com (Cloud)** | **Self-Hosted GPU** |
|---|---|---|
| **Best for** | No GPU hardware, zero maintenance | Own GPU server, full control |
| **Pricing** | Pay-per-use (~$0.01-0.10/min audio) | Fixed infrastructure cost |
| **Setup** | Run from laptop (browser auth) | Run on GPU server |
| **Scaling** | Automatic | Manual |

### Option A: Modal.com (Serverless Cloud GPU)

**Location: YOUR LOCAL COMPUTER (laptop/desktop)**

Modal requires browser authentication, so this runs locally - not on your server.

#### Accept HuggingFace Licenses

Visit both pages and click "Accept":
- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0

Then generate a token at https://huggingface.co/settings/tokens

#### Deploy to Modal

```bash
pip install modal
modal setup  # opens browser for authentication

git clone https://github.com/monadical-sas/reflector.git
cd reflector/gpu/modal_deployments
./deploy-all.sh --hf-token YOUR_HUGGINGFACE_TOKEN
```

**Save the output** - copy the configuration block, you'll need it for Step 4.

See [Modal Setup](./modal-setup) for troubleshooting and details.

### Option B: Self-Hosted GPU

**Location: YOUR GPU SERVER**

Requires: NVIDIA GPU with 8GB+ VRAM, Ubuntu 22.04+, 40-50GB disk (Docker) or 25-30GB (Systemd).

See [Self-Hosted GPU Setup](./self-hosted-gpu-setup) for complete instructions. Quick summary:

1. Install NVIDIA drivers and Docker (or uv for systemd)
2. Clone repository: `git clone https://github.com/monadical-sas/reflector.git`
3. Configure `.env` with HuggingFace token
4. Start service (Docker compose or systemd)
5. Set up Caddy reverse proxy for HTTPS

**Save your API key and HTTPS URL** - you'll need them for Step 4.

---

## Step 3: Prepare Server

**Location: YOUR SERVER (via SSH)**

### Install Docker

```bash
ssh user@your-server-ip

curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Log out and back in for group changes
exit
ssh user@your-server-ip

docker --version  # verify
```

### Firewall

Ensure ports 80 (HTTP) and 443 (HTTPS) are open for inbound traffic. The method varies by cloud provider and OS configuration.

### Clone Repository

```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector
```

---

## Step 4: Configure Environment

**Location: YOUR SERVER (via SSH, in the `reflector` directory)**

Reflector has two env files:
- `server/.env` - Backend configuration
- `www/.env` - Frontend configuration

### Backend Configuration

```bash
cp server/.env.example server/.env
nano server/.env
```

**Required settings:**
```env
# Database (defaults work with docker-compose.prod.yml)
DATABASE_URL=postgresql+asyncpg://reflector:reflector@postgres:5432/reflector

# Redis
REDIS_HOST=redis
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1

# Your domains
BASE_URL=https://api.example.com
CORS_ORIGIN=https://app.example.com
CORS_ALLOW_CREDENTIALS=true

# Secret key - generate with: openssl rand -hex 32
SECRET_KEY=<your-generated-secret>

# GPU Processing - choose ONE option from Step 2:

# Option A: Modal.com (paste from deploy-all.sh output)
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://yourname--reflector-transcriber-web.modal.run
TRANSCRIPT_MODAL_API_KEY=<from-deploy-all.sh-output>
DIARIZATION_BACKEND=modal
DIARIZATION_URL=https://yourname--reflector-diarizer-web.modal.run
DIARIZATION_MODAL_API_KEY=<from-deploy-all.sh-output>

# Option B: Self-hosted GPU (use your GPU server URL and API key)
# TRANSCRIPT_BACKEND=modal
# TRANSCRIPT_URL=https://gpu.example.com
# TRANSCRIPT_MODAL_API_KEY=<your-generated-api-key>
# DIARIZATION_BACKEND=modal
# DIARIZATION_URL=https://gpu.example.com
# DIARIZATION_MODAL_API_KEY=<your-generated-api-key>

# Storage - where to store audio files and transcripts
TRANSCRIPT_STORAGE_BACKEND=local

# LLM - for generating titles, summaries, and topics
LLM_API_KEY=sk-your-openai-api-key
LLM_MODEL=gpt-4o-mini

# Auth - disable for initial setup (see Step 8 for authentication)
AUTH_BACKEND=none
```

### Frontend Configuration

```bash
cp www/.env.example www/.env
nano www/.env
```

**Required settings:**
```env
# Your domains
SITE_URL=https://app.example.com
API_URL=https://api.example.com
WEBSOCKET_URL=wss://api.example.com
SERVER_API_URL=http://server:1250

# NextAuth
NEXTAUTH_URL=https://app.example.com
NEXTAUTH_SECRET=<generate-with-openssl-rand-hex-32>

# Disable login requirement for initial setup
FEATURE_REQUIRE_LOGIN=false
```

---

## Step 5: Configure Caddy

**Location: YOUR SERVER (via SSH)**

```bash
cp Caddyfile.example Caddyfile
nano Caddyfile
```

Replace `example.com` with your domains. The `{$VAR:default}` syntax uses Caddy's env var substitution - you can either edit the file directly or set `FRONTEND_DOMAIN` and `API_DOMAIN` environment variables.

```
{$FRONTEND_DOMAIN:app.example.com} {
    reverse_proxy web:3000
}

{$API_DOMAIN:api.example.com} {
    reverse_proxy server:1250
}
```

---

## Step 6: Start Services

**Location: YOUR SERVER (via SSH)**

```bash
docker compose -f docker-compose.prod.yml up -d
```

Wait for PostgreSQL to be ready, then run migrations:

```bash
# Wait for postgres to be healthy (may take 30-60 seconds on first run)
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U reflector

# Run database migrations
docker compose -f docker-compose.prod.yml exec server uv run alembic upgrade head
```

---

## Step 7: Verify Deployment

### Check services
```bash
docker compose -f docker-compose.prod.yml ps
# All should show "Up"
```

### Check logs for errors
```bash
docker compose -f docker-compose.prod.yml logs server --tail 20
docker compose -f docker-compose.prod.yml logs worker --tail 20
```

### Test API
```bash
curl https://api.example.com/health
# Should return: {"status":"healthy"}
```

### Test Frontend
- Visit https://app.example.com
- You should see the Reflector interface
- Try uploading an audio file to test transcription

---

## Step 8: Enable Authentication (Required for Live Rooms)

By default, Reflector is open (no login required). **Authentication is required if you want to use Live Meeting Rooms (Step 9).**

See [Authentication Setup](./auth-setup) for full Authentik OAuth configuration.

Quick summary:
1. Deploy Authentik on your server
2. Create OAuth provider in Authentik
3. Extract public key for JWT verification
4. Update `server/.env`: `AUTH_BACKEND=jwt` + `AUTH_JWT_AUDIENCE`
5. Update `www/.env`: `FEATURE_REQUIRE_LOGIN=true` + Authentik credentials
6. Mount JWT keys volume and restart services

---

## Step 9: Enable Live Meeting Rooms

**Requires: Step 8 (Authentication)**

Live rooms require Daily.co and AWS S3. See [Daily.co Setup](./daily-setup) for complete S3/IAM configuration instructions.

Quick config - Add to `server/.env`:

```env
DEFAULT_VIDEO_PLATFORM=daily
DAILY_API_KEY=<from-daily.co-dashboard>
DAILY_SUBDOMAIN=<your-daily-subdomain>

# S3 for recording storage
DAILYCO_STORAGE_AWS_BUCKET_NAME=<your-bucket>
DAILYCO_STORAGE_AWS_REGION=us-east-1
DAILYCO_STORAGE_AWS_ROLE_ARN=<arn:aws:iam::ACCOUNT:role/DailyCo>
```

Reload env and restart:
```bash
docker compose -f docker-compose.prod.yml up -d server worker
```

---

## Troubleshooting

### Services won't start
```bash
docker compose -f docker-compose.prod.yml logs
```

### CORS errors in browser
- Verify `CORS_ORIGIN` in `server/.env` matches your frontend domain exactly (including `https://`)
- Reload env: `docker compose -f docker-compose.prod.yml up -d server`

### SSL certificate errors
- Caddy auto-provisions Let's Encrypt certificates
- Ensure ports 80 and 443 are open
- Check: `docker compose -f docker-compose.prod.yml logs caddy`

### Transcription not working
- Check Modal dashboard: https://modal.com/apps
- Verify URLs in `server/.env` match deployed functions
- Check worker logs: `docker compose -f docker-compose.prod.yml logs worker`

### "Login required" but auth not configured
- Set `FEATURE_REQUIRE_LOGIN=false` in `www/.env`
- Rebuild frontend: `docker compose -f docker-compose.prod.yml up -d --force-recreate web`

---

## Next Steps

- [Modal Setup](./modal-setup) - Cloud GPU processing details
- [Self-Hosted GPU Setup](./self-hosted-gpu-setup) - Own GPU server deployment
- [Authentication Setup](./auth-setup) - Authentik OAuth
- [System Requirements](./requirements) - Hardware specs
