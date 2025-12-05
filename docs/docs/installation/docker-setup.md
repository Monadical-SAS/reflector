---
sidebar_position: 3
title: Docker Reference
---

# Docker Reference

This page documents the Docker Compose configuration for Reflector. For the complete deployment guide, see [Deployment Guide](./overview).

## Services

The `docker-compose.prod.yml` includes these services:

| Service | Image | Purpose |
|---------|-------|---------|
| `web` | `monadicalsas/reflector-frontend` | Next.js frontend |
| `server` | `monadicalsas/reflector-backend` | FastAPI backend |
| `worker` | `monadicalsas/reflector-backend` | Celery worker for background tasks |
| `beat` | `monadicalsas/reflector-backend` | Celery beat scheduler |
| `redis` | `redis:7.2-alpine` | Message broker and cache |
| `postgres` | `postgres:17-alpine` | Primary database |
| `caddy` | `caddy:2-alpine` | Reverse proxy with auto-SSL |

## Environment Files

Reflector uses two separate environment files:

### Backend (`server/.env`)

Used by: `server`, `worker`, `beat`

Key variables:
```env
# Database connection
DATABASE_URL=postgresql+asyncpg://reflector:reflector@postgres:5432/reflector

# Redis
REDIS_HOST=redis
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/1

# API domain and CORS
BASE_URL=https://api.example.com
CORS_ORIGIN=https://app.example.com

# Modal GPU processing
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://...
TRANSCRIPT_MODAL_API_KEY=...
```

### Frontend (`www/.env`)

Used by: `web`

Key variables:
```env
# Domain configuration
SITE_URL=https://app.example.com
API_URL=https://api.example.com
WEBSOCKET_URL=wss://api.example.com
SERVER_API_URL=http://server:1250

# Authentication
NEXTAUTH_URL=https://app.example.com
NEXTAUTH_SECRET=...
```

Note: `API_URL` is used client-side (browser), `SERVER_API_URL` is used server-side (SSR).

## Volumes

| Volume | Purpose |
|--------|---------|
| `redis_data` | Redis persistence |
| `postgres_data` | PostgreSQL data |
| `server_data` | Uploaded files, local storage |
| `caddy_data` | SSL certificates |
| `caddy_config` | Caddy configuration |

## Network

All services share the default network. The network is marked `attachable: true` to allow external containers (like Authentik) to join.

## Common Commands

### Start all services
```bash
docker compose -f docker-compose.prod.yml up -d
```

### View logs
```bash
# All services
docker compose -f docker-compose.prod.yml logs -f

# Specific service
docker compose -f docker-compose.prod.yml logs server --tail 50
```

### Restart a service
```bash
docker compose -f docker-compose.prod.yml restart server
```

### Run database migrations
```bash
docker compose -f docker-compose.prod.yml exec server uv run alembic upgrade head
```

### Access database
```bash
docker compose -f docker-compose.prod.yml exec postgres psql -U reflector
```

### Pull latest images
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

### Stop all services
```bash
docker compose -f docker-compose.prod.yml down
```

### Full reset (WARNING: deletes data)
```bash
docker compose -f docker-compose.prod.yml down -v
```

## Customization

### Using a different database

To use an external PostgreSQL:

1. Remove `postgres` service from compose file
2. Update `DATABASE_URL` in `server/.env`:
   ```env
   DATABASE_URL=postgresql+asyncpg://user:pass@external-host:5432/reflector
   ```

### Using external Redis

1. Remove `redis` service from compose file
2. Update Redis settings in `server/.env`:
   ```env
   REDIS_HOST=external-redis-host
   CELERY_BROKER_URL=redis://external-redis-host:6379/1
   ```

### Adding Authentik

To add Authentik for authentication, see [Authentication Setup](./auth-setup). Quick steps:

1. Deploy Authentik separately
2. Connect to Reflector's network:
   ```bash
   docker network connect reflector_default authentik-server-1
   ```
3. Add to Caddyfile:
   ```
   authentik.example.com {
       reverse_proxy authentik-server-1:9000
   }
   ```

## Caddyfile Reference

The Caddyfile supports environment variable substitution:

```
{$FRONTEND_DOMAIN:app.example.com} {
    reverse_proxy web:3000
}

{$API_DOMAIN:api.example.com} {
    reverse_proxy server:1250
}
```

Set `FRONTEND_DOMAIN` and `API_DOMAIN` environment variables, or edit the file directly.

### Reload Caddy after changes
```bash
docker compose -f docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```
