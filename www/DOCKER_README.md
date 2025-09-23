# Docker Production Build Guide

## Overview

The Docker image builds without any environment variables and requires all configuration to be provided at runtime.

## Environment Variables (ALL Runtime)

### Required Runtime Variables

```bash
API_URL             # Backend API URL (e.g., https://api.example.com)
WEBSOCKET_URL       # WebSocket URL (e.g., wss://api.example.com)
NEXTAUTH_URL        # NextAuth base URL (e.g., https://app.example.com)
NEXTAUTH_SECRET     # Random secret for NextAuth (generate with: openssl rand -base64 32)
KV_URL              # Redis URL (e.g., redis://redis:6379)
```

### Optional Runtime Variables

```bash
SITE_URL                    # Frontend URL (defaults to NEXTAUTH_URL)

AUTHENTIK_ISSUER            # OAuth issuer URL
AUTHENTIK_CLIENT_ID         # OAuth client ID
AUTHENTIK_CLIENT_SECRET     # OAuth client secret
AUTHENTIK_REFRESH_TOKEN_URL # OAuth token refresh URL

FEATURE_REQUIRE_LOGIN=false # Require authentication
FEATURE_PRIVACY=true        # Enable privacy features
FEATURE_BROWSE=true         # Enable browsing features
FEATURE_SEND_TO_ZULIP=false # Enable Zulip integration
FEATURE_ROOMS=true          # Enable rooms feature

SENTRY_DSN                  # Sentry error tracking
AUTH_CALLBACK_URL          # OAuth callback URL
```

## Building the Image

### Option 1: Using Docker Compose

1. Build the image (no environment variables needed):

```bash
docker compose -f docker-compose.prod.yml build
```

2. Create a `.env` file with runtime variables

3. Run with environment variables:

```bash
docker compose -f docker-compose.prod.yml --env-file .env up -d
```

### Option 2: Using Docker CLI

1. Build the image (no build args):

```bash
docker build -t reflector-frontend:latest ./www
```

2. Run with environment variables:

```bash
docker run -d \
  -p 3000:3000 \
  -e API_URL=https://api.example.com \
  -e WEBSOCKET_URL=wss://api.example.com \
  -e NEXTAUTH_URL=https://app.example.com \
  -e NEXTAUTH_SECRET=your-secret \
  -e KV_URL=redis://redis:6379 \
  -e AUTHENTIK_ISSUER=https://auth.example.com/application/o/reflector \
  -e AUTHENTIK_CLIENT_ID=your-client-id \
  -e AUTHENTIK_CLIENT_SECRET=your-client-secret \
  -e AUTHENTIK_REFRESH_TOKEN_URL=https://auth.example.com/application/o/token/ \
  -e FEATURE_REQUIRE_LOGIN=true \
  reflector-frontend:latest
```
