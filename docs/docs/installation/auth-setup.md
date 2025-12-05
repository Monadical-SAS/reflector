---
sidebar_position: 5
title: Authentication Setup
---

# Authentication Setup

This page covers authentication setup in detail. For the complete deployment guide, see [Deployment Guide](./overview).

Reflector uses [Authentik](https://goauthentik.io/) for OAuth/OIDC authentication. This guide walks you through setting up Authentik and connecting it to Reflector.

## Overview

Reflector's authentication flow:
1. User clicks "Sign In" on frontend
2. Frontend redirects to Authentik login page
3. User authenticates with Authentik
4. Authentik redirects back with OAuth tokens
5. Frontend stores tokens, backend verifies JWT signature

## Option 1: Self-Hosted Authentik (Same Server)

This setup runs Authentik on the same server as Reflector, with Caddy proxying to both.

### Step 1: Deploy Authentik

```bash
# Create directory for Authentik
mkdir -p ~/authentik && cd ~/authentik

# Download docker-compose file
curl -O https://goauthentik.io/docker-compose.yml

# Generate secrets and bootstrap credentials
cat > .env << 'EOF'
PG_PASS=$(openssl rand -base64 36 | tr -d '\n')
AUTHENTIK_SECRET_KEY=$(openssl rand -base64 60 | tr -d '\n')
AUTHENTIK_ERROR_REPORTING__ENABLED=false
AUTHENTIK_BOOTSTRAP_PASSWORD=YourSecurePassword123
AUTHENTIK_BOOTSTRAP_EMAIL=admin@example.com
EOF

# Start Authentik
sudo docker compose up -d
```

Authentik takes ~2 minutes to run migrations and apply blueprints on first start.

### Step 2: Connect Authentik to Reflector's Network

Since Authentik runs in a separate Docker Compose project, connect it to Reflector's network so Caddy can proxy to it:

```bash
# Wait for Authentik to be healthy
sleep 120

# Connect Authentik server to Reflector's network
sudo docker network connect reflector_default authentik-server-1
```

**Important:** This step must be repeated if you restart Authentik with `docker compose down`. Add it to your deployment scripts or use `docker compose up -d` (which preserves containers) instead of down/up.

### Step 3: Add Authentik to Caddy

Edit your `Caddyfile` to add the Authentik domain:

```
app.example.com {
    reverse_proxy web:3000
}

api.example.com {
    reverse_proxy server:1250
}

authentik.example.com {
    reverse_proxy authentik-server-1:9000
}
```

Reload Caddy:
```bash
sudo docker exec reflector-caddy-1 caddy reload --config /etc/caddy/Caddyfile
```

### Step 4: Create OAuth2 Provider in Authentik

1. **Login to Authentik Admin** at `https://authentik.example.com/`
   - Username: `akadmin`
   - Password: The `AUTHENTIK_BOOTSTRAP_PASSWORD` you set in .env

2. **Create OAuth2 Provider:**
   - Go to **Applications > Providers > Create**
   - Select **OAuth2/OpenID Provider**
   - Configure:
     - **Name**: `Reflector`
     - **Authorization flow**: `default-provider-authorization-implicit-consent`
     - **Client type**: `Confidential`
     - **Client ID**: Note this value (auto-generated)
     - **Client Secret**: Note this value (auto-generated)
     - **Redirect URIs**: Add entry with:
       ```
       https://app.example.com/api/auth/callback/authentik
       ```
   - Click **Finish**

3. **Create Application:**
   - Go to **Applications > Applications > Create**
   - Configure:
     - **Name**: `Reflector`
     - **Slug**: `reflector` (auto-filled)
     - **Provider**: Select the `Reflector` provider you just created
   - Click **Create**

### Step 5: Get Public Key for JWT Verification

Extract the public key from Authentik's JWKS endpoint:

```bash
curl -s https://authentik.example.com/application/o/reflector/jwks/ | \
  jq -r '.keys[0].x5c[0]' | base64 -d | openssl x509 -pubkey -noout \
  > ~/reflector/server/reflector/auth/jwt/keys/authentik_public.pem
```

### Step 6: Update docker-compose.prod.yml

Add a volume mount for the JWT keys directory to the server and worker services:

```yaml
server:
  image: monadicalsas/reflector-backend:latest
  # ... other config ...
  volumes:
    - server_data:/app/data
    - ./server/reflector/auth/jwt/keys:/app/reflector/auth/jwt/keys:ro

worker:
  image: monadicalsas/reflector-backend:latest
  # ... other config ...
  volumes:
    - server_data:/app/data
    - ./server/reflector/auth/jwt/keys:/app/reflector/auth/jwt/keys:ro
```

### Step 7: Configure Reflector Backend

Update `server/.env`:
```env
# Authentication
AUTH_BACKEND=jwt
AUTH_JWT_PUBLIC_KEY=authentik_public.pem
AUTH_JWT_AUDIENCE=<your-client-id>
CORS_ALLOW_CREDENTIALS=true
```

Replace `<your-client-id>` with the Client ID from Step 4.

### Step 8: Configure Reflector Frontend

Update `www/.env`:
```env
# Authentication
FEATURE_REQUIRE_LOGIN=true

# Authentik OAuth
AUTHENTIK_ISSUER=https://authentik.example.com/application/o/reflector
AUTHENTIK_REFRESH_TOKEN_URL=https://authentik.example.com/application/o/token/
AUTHENTIK_CLIENT_ID=<your-client-id>
AUTHENTIK_CLIENT_SECRET=<your-client-secret>

# NextAuth
NEXTAUTH_SECRET=<generate-with-openssl-rand-hex-32>
```

### Step 9: Restart Services

```bash
cd ~/reflector
sudo docker compose -f docker-compose.prod.yml up -d --force-recreate server worker web
```

### Step 10: Verify Authentication

1. Visit `https://app.example.com`
2. Click "Log in" or navigate to `/api/auth/signin`
3. Click "Sign in with Authentik"
4. Login with your Authentik credentials
5. You should be redirected back and see "Log out" in the header

## Option 2: Disable Authentication

For testing or internal deployments where authentication isn't needed:

**Backend `server/.env`:**
```env
AUTH_BACKEND=none
```

**Frontend `www/.env`:**
```env
FEATURE_REQUIRE_LOGIN=false
```

**Note:** The pre-built Docker images have `FEATURE_REQUIRE_LOGIN=true` baked in. To disable auth, you'll need to rebuild the frontend image with the env var set at build time, or set up Authentik.

## Troubleshooting

### "Invalid redirect URI" error
- Verify the redirect URI in Authentik matches exactly:
  ```
  https://app.example.com/api/auth/callback/authentik
  ```
- Check for trailing slashes - they must match exactly

### "Invalid audience" JWT error
- Ensure `AUTH_JWT_AUDIENCE` in `server/.env` matches the Client ID from Authentik
- The audience value is the OAuth Client ID, not the issuer URL

### "JWT verification failed" error
- Verify the public key file is mounted in the container
- Check `AUTH_JWT_PUBLIC_KEY` points to the correct filename
- Ensure the key was extracted from the correct provider's JWKS endpoint

### Caddy returns 503 for Authentik
- Verify Authentik container is connected to Reflector's network:
  ```bash
  sudo docker network connect reflector_default authentik-server-1
  ```
- Check Authentik is healthy: `cd ~/authentik && sudo docker compose ps`

### Users can't access protected pages
- Verify `FEATURE_REQUIRE_LOGIN=true` in frontend
- Check `AUTH_BACKEND=jwt` in backend
- Verify CORS settings allow credentials

### Token refresh errors
- Ensure Redis is running (frontend uses Redis for token caching)
- Verify `KV_URL` is set correctly in frontend env
- Check `AUTHENTIK_REFRESH_TOKEN_URL` is correct

## API Key Authentication

For programmatic access (scripts, integrations), users can generate API keys:

1. Login to Reflector
2. Go to Settings > API Keys
3. Click "Generate New Key"
4. Use the key in requests:
   ```bash
   curl -H "X-API-Key: your-api-key" https://api.example.com/v1/transcripts
   ```

API keys are stored hashed and can be revoked at any time.
