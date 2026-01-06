---
sidebar_position: 10
title: Docs Website Deployment
---

# Docs Website Deployment

This guide covers deploying the Reflector documentation website. **This is optional and intended for internal/experimental use only.**

## Overview

The documentation is built using Docusaurus and deployed as a static nginx-served site.

## Prerequisites

- Reflector already deployed (Steps 1-7 from [Deployment Guide](./overview))
- DNS A record for docs subdomain (e.g., `docs.example.com`)

## Deployment Steps

### Step 1: Pre-fetch OpenAPI Spec

The docs site includes API reference from your running backend. Fetch it before building:

```bash
cd ~/reflector
docker compose -f docker-compose.prod.yml exec server curl -s http://localhost:1250/openapi.json > docs/static/openapi.json
```

This creates `docs/static/openapi.json` (should be ~70KB) which will be copied during Docker build.

**Why not fetch during build?** Docker build containers are network-isolated and can't access the running backend services.

### Step 2: Verify Dockerfile

The Dockerfile is already in `docs/Dockerfile`:

```dockerfile
FROM node:18-alpine AS builder
WORKDIR /app

# Copy package files
COPY package*.json ./

# Inshall dependencies
RUN npm ci

# Copy source (includes static/openapi.json if pre-fetched)
COPY . .

# Fix docusaurus config: change onBrokenLinks to 'warn' for Docker build
RUN sed -i "s/onBrokenLinks: 'throw'/onBrokenLinks: 'warn'/g" docusaurus.config.ts

# Build static site
RUN npx docusaurus build

FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

### Step 3: Add Docs Service to docker-compose.prod.yml

Add this service to `docker-compose.prod.yml`:

```yaml
docs:
  build: ./docs
  restart: unless-stopped
  networks:
    - default
```

### Step 4: Add Caddy Route

Add to `Caddyfile`:

```
{$DOCS_DOMAIN:docs.example.com} {
    reverse_proxy docs:80
}
```

### Step 5: Build and Deploy

```bash
cd ~/reflector
docker compose -f docker-compose.prod.yml up -d --build docs
docker compose -f docker-compose.prod.yml exec caddy caddy reload --config /etc/caddy/Caddyfile
```

### Step 6: Verify

```bash
# Check container status
docker compose -f docker-compose.prod.yml ps docs
# Should show "Up"

# Test URL
curl -I https://docs.example.com
# Should return HTTP/2 200
```

Visit `https://docs.example.com` in your browser

## Updating Documentation

When docs are updated:

```bash
cd ~/reflector
git pull

# Refresh OpenAPI spec from backend
docker compose -f docker-compose.prod.yml exec server curl -s http://localhost:1250/openapi.json > docs/static/openapi.json

# Rebuild docs
docker compose -f docker-compose.prod.yml up -d --build docs
```

## Troubleshooting

### Missing openapi.json during build
- Make sure you ran the pre-fetch step first (Step 1)
- Verify `docs/static/openapi.json` exists and is ~70KB
- Re-run: `docker compose exec server curl -s http://localhost:1250/openapi.json > docs/static/openapi.json`

### Build fails with "Docusaurus found broken links"
- This happens if `onBrokenLinks: 'throw'` is set in docusaurus.config.ts
- Solution is already in Dockerfile: uses `sed` to change to `'warn'` during build

### 404 on all pages
- Docusaurus baseUrl might be wrong - should be `/` for custom domain
- Check `docs/docusaurus.config.ts`: `baseUrl: '/'`

### Docs not updating after rebuild
- Force rebuild: `docker compose -f docker-compose.prod.yml build --no-cache docs`
- Then: `docker compose -f docker-compose.prod.yml up -d docs`
