#!/bin/bash
set -e

# Setup Authentik OAuth provider for Reflector
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

# Step 1: Create API token using basic auth
echo "Creating API token..."
TOKEN_RESPONSE=$(curl -s -X POST "$AUTHENTIK_URL/api/v3/core/tokens/" \
    -u "akadmin:$ADMIN_PASSWORD" \
    -H "Content-Type: application/json" \
    -d '{
        "identifier": "reflector-setup-token",
        "intent": "api",
        "description": "Token for Reflector setup script"
    }')

# Check if token already exists, if so get it
if echo "$TOKEN_RESPONSE" | grep -q "already exists"; then
    echo "  -> Token exists, retrieving..."
    API_TOKEN=$(curl -s "$AUTHENTIK_URL/api/v3/core/tokens/reflector-setup-token/view_key/" \
        -u "akadmin:$ADMIN_PASSWORD" | jq -r '.key')
else
    API_TOKEN=$(echo "$TOKEN_RESPONSE" | jq -r '.key')
fi

if [ -z "$API_TOKEN" ] || [ "$API_TOKEN" = "null" ]; then
    echo "Error: Failed to get API token"
    echo "Response: $TOKEN_RESPONSE"
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
SCOPE_RESPONSE=$(curl -s "$AUTHENTIK_URL/api/v3/propertymappings/scope/" \
    -H "Authorization: Bearer $API_TOKEN")

EMAIL_SCOPE=$(echo "$SCOPE_RESPONSE" | jq -r '.results[] | select(.scope_name=="email") | .pk')
OPENID_SCOPE=$(echo "$SCOPE_RESPONSE" | jq -r '.results[] | select(.scope_name=="openid") | .pk')
PROFILE_SCOPE=$(echo "$SCOPE_RESPONSE" | jq -r '.results[] | select(.scope_name=="profile") | .pk')
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

# Step 9: Clean up setup token
echo "Cleaning up..."
curl -s -X DELETE "$AUTHENTIK_URL/api/v3/core/tokens/reflector-setup-token/" \
    -H "Authorization: Bearer $API_TOKEN" > /dev/null 2>&1 || true

# Output configuration
echo ""
echo "==========================================="
echo "Setup complete!"
echo "==========================================="
echo ""
echo "Add these to your www/.env file:"
echo ""
echo "# --- Authentik OAuth Configuration ---"
echo "AUTHENTIK_ISSUER=$AUTHENTIK_URL/application/o/reflector"
echo "AUTHENTIK_REFRESH_TOKEN_URL=$AUTHENTIK_URL/application/o/token/"
echo "AUTHENTIK_CLIENT_ID=$CLIENT_ID"
echo "AUTHENTIK_CLIENT_SECRET=$CLIENT_SECRET"
echo "# --- End Authentik Configuration ---"
echo ""
echo "Add this to your server/.env file:"
echo ""
echo "# --- JWT Authentication ---"
echo "AUTH_BACKEND=jwt"
echo "AUTH_JWT_AUDIENCE=$CLIENT_ID"
echo "# --- End JWT Configuration ---"
