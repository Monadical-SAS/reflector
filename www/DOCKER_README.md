# Docker Production Build Guide

## Environment Variables

### Required Build-time Variables (Must be provided for `docker build`)

```bash
NEXT_PUBLIC_API_URL         # Backend API URL (e.g., https://api.example.com) - REQUIRED
NEXT_PUBLIC_WEBSOCKET_URL   # WebSocket URL (e.g., wss://api.example.com) - REQUIRED
```

### Optional Build-time Variables (Provide based on your setup)

```bash
NEXT_PUBLIC_SITE_URL        # Frontend URL (e.g., https://app.example.com)

# Authentication variables (only needed if NEXT_PUBLIC_FEATURE_REQUIRE_LOGIN=true)
NEXTAUTH_URL                # NextAuth base URL (usually same as NEXT_PUBLIC_SITE_URL)
NEXTAUTH_SECRET             # Random secret for NextAuth (generate with: openssl rand -base64 32)
AUTHENTIK_ISSUER            # OAuth issuer URL (e.g., https://auth.example.com/application/o/app)
AUTHENTIK_CLIENT_ID         # OAuth client ID
AUTHENTIK_CLIENT_SECRET     # OAuth client secret
AUTHENTIK_REFRESH_TOKEN_URL # OAuth token refresh URL
```

### Runtime Variables (Required for `docker run`)

```bash
KV_URL                      # Redis URL (e.g., redis://redis:6379)
# Plus all the build-time variables need to be provided at runtime too
```

## Building the Image

### Option 1: Using Docker Compose (Recommended)

Create a `.env` file with all required variables:

```bash
# Build variables
NEXT_PUBLIC_SITE_URL=https://app.example.com
NEXT_PUBLIC_API_URL=https://api.example.com
NEXT_PUBLIC_WEBSOCKET_URL=wss://api.example.com
NEXTAUTH_URL=https://app.example.com
NEXTAUTH_SECRET=your-random-secret-here
AUTHENTIK_ISSUER=https://auth.example.com/application/o/reflector
AUTHENTIK_CLIENT_ID=your-client-id
AUTHENTIK_CLIENT_SECRET=your-client-secret
AUTHENTIK_REFRESH_TOKEN_URL=https://auth.example.com/application/o/token/

# Runtime variables
KV_URL=redis://redis:6379
```

Then build and run:

```bash
docker compose -f compose.prod.yml build
docker compose -f compose.prod.yml up -d web
```

### Option 2: Using Docker CLI

```bash
# Minimal build (no authentication)
docker build \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.com \
  --build-arg NEXT_PUBLIC_WEBSOCKET_URL=wss://api.example.com \
  -t reflector-frontend:latest \
  ./www

# Full build with authentication
docker build \
  --build-arg NEXT_PUBLIC_SITE_URL=https://app.example.com \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.com \
  --build-arg NEXT_PUBLIC_WEBSOCKET_URL=wss://api.example.com \
  --build-arg NEXTAUTH_URL=https://app.example.com \
  --build-arg NEXTAUTH_SECRET=your-secret \
  --build-arg AUTHENTIK_ISSUER=https://auth.example.com/application/o/reflector \
  --build-arg AUTHENTIK_CLIENT_ID=your-client-id \
  --build-arg AUTHENTIK_CLIENT_SECRET=your-client-secret \
  --build-arg AUTHENTIK_REFRESH_TOKEN_URL=https://auth.example.com/application/o/token/ \
  -t reflector-frontend:latest \
  ./www
```

Then run:

```bash
docker run -d \
  -p 3000:3000 \
  -e KV_URL=redis://redis:6379 \
  -e NEXTAUTH_URL=https://app.example.com \
  -e NEXTAUTH_SECRET=your-secret \
  -e AUTHENTIK_ISSUER=https://auth.example.com/application/o/reflector \
  -e AUTHENTIK_CLIENT_ID=your-client-id \
  -e AUTHENTIK_CLIENT_SECRET=your-client-secret \
  -e AUTHENTIK_REFRESH_TOKEN_URL=https://auth.example.com/application/o/token/ \
  reflector-frontend:latest
```

## Health Check

The container includes a health check endpoint at `/api/health` that verifies:

- Redis connectivity
- Memory usage
- General application health

```bash
curl http://localhost:3000/api/health
```

## Important Notes

1. **No .env files in the image**: The production build does not include any `.env` files. All configuration must be provided via environment variables.

2. **Build will fail without variables**: If any required variable is missing, the build will fail with an error. This is intentional to prevent deploying broken builds.

3. **Secrets management**: Never commit secrets to version control. Use a secrets management system (Kubernetes Secrets, Docker Swarm Secrets, AWS Secrets Manager, etc.) in production.

4. **NEXTAUTH_SECRET**: Generate a strong secret with:

   ```bash
   openssl rand -base64 32
   ```

5. **Network naming**: When using Docker Compose, services can reference each other by name (e.g., `redis`, `server`). In Kubernetes or other orchestrators, adjust URLs accordingly.
