---
sidebar_position: 1
title: Deployment Guide
---

# Deployment Guide

This guide walks you through deploying Reflector from scratch. Follow these steps in order.

## What You'll Set Up

```
User --> Caddy (auto-SSL) --> Frontend (Next.js)
                         --> Backend (FastAPI) --> PostgreSQL
                                               --> Redis
                                               --> Celery Workers --> Modal.com GPU
```

## Prerequisites

Before starting, you need:

- [ ] **Production server** - Ubuntu 22.04+, 4+ cores, 8GB+ RAM, public IP
- [ ] **Two domain names** - e.g., `app.example.com` (frontend) and `api.example.com` (backend)
- [ ] **Modal.com account** - Free tier at https://modal.com
- [ ] **HuggingFace account** - Free at https://huggingface.co

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

## Step 2: Deploy Modal GPU Functions

**Location: YOUR LOCAL COMPUTER (laptop/desktop)**

Modal requires browser authentication, so this runs locally - not on your server.

### Accept HuggingFace Licenses

Visit both pages and click "Accept":
- https://huggingface.co/pyannote/speaker-diarization-3.1
- https://huggingface.co/pyannote/segmentation-3.0

Then generate a token at https://huggingface.co/settings/tokens

### Deploy to Modal

```bash
pip install modal
modal setup  # opens browser for authentication

git clone https://github.com/monadical-sas/reflector.git
cd reflector/gpu/modal_deployments
./deploy-all.sh --hf-token YOUR_HUGGINGFACE_TOKEN
```

**Save the output** - copy the configuration block, you'll need it for Step 5.

See [Modal Setup](./modal-setup) for troubleshooting and details.

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

### Open Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

### Clone Repository

```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector
```

---

## Step 4: Configure Environment

**Location: YOUR SERVER (via SSH)**

Reflector has two env files:
- `server/.env` - Backend configuration
- `www/.env` - Frontend configuration

### Backend Configuration

```bash
cp server/env.example server/.env
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

# Modal GPU (paste from deploy-all.sh output)
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://yourname--reflector-transcriber-web.modal.run
TRANSCRIPT_MODAL_API_KEY=<from-deploy-all.sh-output>

DIARIZATION_BACKEND=modal
DIARIZATION_URL=https://yourname--reflector-diarizer-web.modal.run
DIARIZATION_MODAL_API_KEY=<from-deploy-all.sh-output>

# Auth - disable for initial setup (see Step 9 for authentication)
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

Replace `example.com` with your domains:
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

Wait for containers to start (~30 seconds), then run migrations:

```bash
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

Live rooms require Daily.co and AWS S3. Add to `server/.env`:

```env
DEFAULT_VIDEO_PLATFORM=daily
DAILY_API_KEY=<from-daily.co-dashboard>
DAILY_SUBDOMAIN=<your-daily-subdomain>

# S3 for recording storage
DAILYCO_STORAGE_AWS_BUCKET_NAME=<your-bucket>
DAILYCO_STORAGE_AWS_REGION=us-east-1
DAILYCO_STORAGE_AWS_ROLE_ARN=<arn:aws:iam::ACCOUNT:role/DailyCo>
```

Restart server:
```bash
docker compose -f docker-compose.prod.yml restart server worker
```

---

## Troubleshooting

### Services won't start
```bash
docker compose -f docker-compose.prod.yml logs
```

### CORS errors in browser
- Verify `CORS_ORIGIN` in `server/.env` matches your frontend domain exactly (including `https://`)
- Restart: `docker compose -f docker-compose.prod.yml restart server`

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

- [Modal Setup](./modal-setup) - GPU processing details
- [Authentication Setup](./auth-setup) - Authentik OAuth
- [System Requirements](./requirements) - Hardware specs
