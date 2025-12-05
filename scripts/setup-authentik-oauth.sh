#!/bin/bash
set -e

# Setup Authentik OAuth provider for Reflector
#
# IMPORTANT: Run this script from your Reflector repository directory (cd ~/reflector)
# The script creates files using relative paths: server/reflector/auth/jwt/keys/
#
# Usage: ./setup-authentik-oauth.sh <authentik-url> <admin-password> <frontend-url>
# Example: ./setup-authentik-oauth.sh https://authentik.example.com MyPassword123 https://app.example.com

AUTHENTIK_URL="${1:-}"
ADMIN_PASSWORD="${2:-}"
FRONTEND_URL="${3:-}"

if [ -z "$AUTHENTIK_URL" ] || [ -z "$ADMIN_PASSWORD" ] || [ -z "$FRONTEND_URL" ]; then
    echo "Usage: $0 <authentik-url> <admin-password> <frontend-url>"
    echo "Example: $0 https://authentik.example.com MyPassword123 https://app.example.com"
    exit 1
fi

# Remove trailing slash from URLs
AUTHENTIK_URL="${AUTHENTIK_URL%/}"
FRONTEND_URL="${FRONTEND_URL%/}"

echo "==========================================="
echo "Authentik OAuth Setup for Reflector"
echo "==========================================="
echo ""
echo "Authentik URL: $AUTHENTIK_URL"
echo "Frontend URL: $FRONTEND_URL"
echo ""

# Step 1: Create API token via Django shell
echo "Creating API token..."
cd ~/authentik || { echo "Error: ~/authentik directory not found"; exit 1; }

API_TOKEN=$(sudo docker compose exec -T server python -m manage shell 2>&1 << 'PYTHON' | grep "^TOKEN:" | cut -d: -f2
from authentik.core.models import User, Token, TokenIntents

user = User.objects.get(username='akadmin')
token, created = Token.objects.update_or_create(
    identifier='reflector-setup',
    defaults={
        'user': user,
        'intent': TokenIntents.INTENT_API,
        'description': 'Reflector setup token',
        'expiring': False
    }
)
print(f"TOKEN:{token.key}")
PYTHON
)

cd - > /dev/null

if [ -z "$API_TOKEN" ] || [ "$API_TOKEN" = "null" ]; then
    echo "Error: Failed to create API token"
    echo "Make sure Authentik is fully started and akadmin user exists"
    exit 1
fi
echo "  -> Got API token"

# Step 2: Get authorization flow UUID
echo "Getting authorization flow..."
FLOW_RESPONSE=$(curl -s "$AUTHENTIK_URL/api/v3/flows/instances/?slug=default-provider-authorization-implicit-consent" \
    -H "Authorization: Bearer $API_TOKEN")

FLOW_UUID=$(echo "$FLOW_RESPONSE" | jq -r '.results[0].pk')
if [ -z "$FLOW_UUID" ] || [ "$FLOW_UUID" = "null" ]; then
    echo "Error: Could not find authorization flow"
    echo "Response: $FLOW_RESPONSE"
    exit 1
fi
echo "  -> Flow UUID: $FLOW_UUID"

# Step 3: Get invalidation flow UUID
echo "Getting invalidation flow..."
INVALIDATION_RESPONSE=$(curl -s "$AUTHENTIK_URL/api/v3/flows/instances/?slug=default-provider-invalidation-flow" \
    -H "Authorization: Bearer $API_TOKEN")

INVALIDATION_UUID=$(echo "$INVALIDATION_RESPONSE" | jq -r '.results[0].pk')
if [ -z "$INVALIDATION_UUID" ] || [ "$INVALIDATION_UUID" = "null" ]; then
    echo "Warning: Could not find invalidation flow, using authorization flow"
    INVALIDATION_UUID="$FLOW_UUID"
fi
echo "  -> Invalidation UUID: $INVALIDATION_UUID"

# Step 4: Get scope mappings (email, openid, profile)
echo "Getting scope mappings..."
SCOPE_RESPONSE=$(curl -s "$AUTHENTIK_URL/api/v3/propertymappings/all/" \
    -H "Authorization: Bearer $API_TOKEN")

EMAIL_SCOPE=$(echo "$SCOPE_RESPONSE" | jq -r '.results[] | select(.name == "authentik default OAuth Mapping: OpenID '\''email'\''") | .pk')
OPENID_SCOPE=$(echo "$SCOPE_RESPONSE" | jq -r '.results[] | select(.name == "authentik default OAuth Mapping: OpenID '\''openid'\''") | .pk')
PROFILE_SCOPE=$(echo "$SCOPE_RESPONSE" | jq -r '.results[] | select(.name == "authentik default OAuth Mapping: OpenID '\''profile'\''") | .pk')
echo "  -> email: $EMAIL_SCOPE"
echo "  -> openid: $OPENID_SCOPE"
echo "  -> profile: $PROFILE_SCOPE"

# Step 5: Get signing key
echo "Getting signing key..."
CERT_RESPONSE=$(curl -s "$AUTHENTIK_URL/api/v3/crypto/certificatekeypairs/" \
    -H "Authorization: Bearer $API_TOKEN")
SIGNING_KEY=$(echo "$CERT_RESPONSE" | jq -r '.results[0].pk')
echo "  -> Signing key: $SIGNING_KEY"

# Step 6: Generate client credentials
CLIENT_ID="reflector"
CLIENT_SECRET=$(openssl rand -hex 32)

# Step 7: Create OAuth2 provider
echo "Creating OAuth2 provider..."
PROVIDER_RESPONSE=$(curl -s -X POST "$AUTHENTIK_URL/api/v3/providers/oauth2/" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Reflector\",
        \"authorization_flow\": \"$FLOW_UUID\",
        \"invalidation_flow\": \"$INVALIDATION_UUID\",
        \"client_type\": \"confidential\",
        \"client_id\": \"$CLIENT_ID\",
        \"client_secret\": \"$CLIENT_SECRET\",
        \"redirect_uris\": [{
            \"matching_mode\": \"strict\",
            \"url\": \"$FRONTEND_URL/api/auth/callback/authentik\"
        }],
        \"property_mappings\": [\"$EMAIL_SCOPE\", \"$OPENID_SCOPE\", \"$PROFILE_SCOPE\"],
        \"signing_key\": \"$SIGNING_KEY\",
        \"access_token_validity\": \"hours=1\",
        \"refresh_token_validity\": \"days=30\"
    }")

PROVIDER_ID=$(echo "$PROVIDER_RESPONSE" | jq -r '.pk')
if [ -z "$PROVIDER_ID" ] || [ "$PROVIDER_ID" = "null" ]; then
    # Check if provider already exists
    if echo "$PROVIDER_RESPONSE" | grep -q "already exists"; then
        echo "  -> Provider already exists, updating..."
        EXISTING=$(curl -s "$AUTHENTIK_URL/api/v3/providers/oauth2/?name=Reflector" \
            -H "Authorization: Bearer $API_TOKEN")
        PROVIDER_ID=$(echo "$EXISTING" | jq -r '.results[0].pk')
        CLIENT_ID=$(echo "$EXISTING" | jq -r '.results[0].client_id')
        # Update secret and scopes
        curl -s -X PATCH "$AUTHENTIK_URL/api/v3/providers/oauth2/$PROVIDER_ID/" \
            -H "Authorization: Bearer $API_TOKEN" \
            -H "Content-Type: application/json" \
            -d "{
                \"client_secret\": \"$CLIENT_SECRET\",
                \"property_mappings\": [\"$EMAIL_SCOPE\", \"$OPENID_SCOPE\", \"$PROFILE_SCOPE\"],
                \"signing_key\": \"$SIGNING_KEY\"
            }" > /dev/null
    else
        echo "Error: Failed to create provider"
        echo "Response: $PROVIDER_RESPONSE"
        exit 1
    fi
fi
echo "  -> Provider ID: $PROVIDER_ID"

# Step 8: Create application
echo "Creating application..."
APP_RESPONSE=$(curl -s -X POST "$AUTHENTIK_URL/api/v3/core/applications/" \
    -H "Authorization: Bearer $API_TOKEN" \
    -H "Content-Type: application/json" \
    -d "{
        \"name\": \"Reflector\",
        \"slug\": \"reflector\",
        \"provider\": $PROVIDER_ID
    }")

if echo "$APP_RESPONSE" | grep -q "already exists"; then
    echo "  -> Application already exists"
else
    APP_SLUG=$(echo "$APP_RESPONSE" | jq -r '.slug')
    if [ -z "$APP_SLUG" ] || [ "$APP_SLUG" = "null" ]; then
        echo "Error: Failed to create application"
        echo "Response: $APP_RESPONSE"
        exit 1
    fi
    echo "  -> Application created: $APP_SLUG"
fi

# Step 9: Extract public key for JWT verification
echo "Extracting public key for JWT verification..."
mkdir -p server/reflector/auth/jwt/keys
curl -s "$AUTHENTIK_URL/application/o/reflector/jwks/" | \
    jq -r '.keys[0].x5c[0]' | \
    base64 -d | \
    openssl x509 -pubkey -noout > server/reflector/auth/jwt/keys/authentik_public.pem

if [ ! -s server/reflector/auth/jwt/keys/authentik_public.pem ]; then
    echo "Error: Failed to extract public key"
    exit 1
fi
echo "  -> Saved to server/reflector/auth/jwt/keys/authentik_public.pem"

# Step 10: Update environment files automatically
echo "Updating environment files..."

# Update server/.env
cat >> server/.env << EOF

# --- Authentik OAuth (added by setup script) ---
AUTH_BACKEND=jwt
AUTH_JWT_AUDIENCE=$CLIENT_ID
AUTH_JWT_PUBLIC_KEY=authentik_public.pem
# --- End JWT Configuration ---
EOF
echo "  -> Updated server/.env"

# Update www/.env
cat >> www/.env << EOF

# --- Authentik OAuth (added by setup script) ---
FEATURE_REQUIRE_LOGIN=true
AUTHENTIK_ISSUER=$AUTHENTIK_URL/application/o/reflector
AUTHENTIK_REFRESH_TOKEN_URL=$AUTHENTIK_URL/application/o/token/
AUTHENTIK_CLIENT_ID=$CLIENT_ID
AUTHENTIK_CLIENT_SECRET=$CLIENT_SECRET
# --- End Authentik Configuration ---
EOF
echo "  -> Updated www/.env"

# Step 11: Restart Reflector services
echo "Restarting Reflector services..."
docker compose -f docker-compose.prod.yml up -d server worker web

echo ""
echo "==========================================="
echo "Setup complete!"
echo "==========================================="
echo ""
echo "Authentik admin: $AUTHENTIK_URL"
echo "  Username: akadmin"
echo "  Password: (provided as argument)"
echo ""
echo "Frontend: $FRONTEND_URL"
echo "  Authentication is now required"
echo ""
echo "Note: Public key saved to server/reflector/auth/jwt/keys/authentik_public.pem"
echo "      and mounted via docker-compose volume."
echo ""
