#!/bin/bash

# Script to fetch OpenAPI specification from FastAPI backend
# Used during documentation build process

set -e

echo "📡 Fetching OpenAPI specification from FastAPI backend..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="../server"
OPENAPI_OUTPUT="./static/openapi.json"
SERVER_PORT=1250  # Reflector uses port 1250 by default
MAX_WAIT=30

# Check if backend directory exists
if [ ! -d "$BACKEND_DIR" ]; then
    echo -e "${RED}Error: Backend directory not found at $BACKEND_DIR${NC}"
    exit 1
fi

# Function to check if server is running
check_server() {
    curl -s -o /dev/null -w "%{http_code}" "http://localhost:${SERVER_PORT}/openapi.json" 2>/dev/null
}

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo -e "\n${YELLOW}Stopping FastAPI server (PID: $SERVER_PID)...${NC}"
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
}

# Set trap to cleanup on exit
trap cleanup EXIT INT TERM

# Change to backend directory
cd "$BACKEND_DIR"

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo -e "${YELLOW}uv not found, checking for python...${NC}"
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}Error: Neither uv nor python found${NC}"
        exit 1
    fi
    RUN_CMD="$PYTHON_CMD -m"
else
    RUN_CMD="uv run -m"
fi

# Start the FastAPI server in the background (let it use default port 1250)
echo -e "${YELLOW}Starting FastAPI server...${NC}"
$RUN_CMD reflector.app > /dev/null 2>&1 &
SERVER_PID=$!

# Wait for server to be ready
echo -n "Waiting for server to be ready"
WAITED=0
while [ $WAITED -lt $MAX_WAIT ]; do
    if [ "$(check_server)" = "200" ]; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
    WAITED=$((WAITED + 1))
done

if [ $WAITED -ge $MAX_WAIT ]; then
    echo -e " ${RED}✗${NC}"
    echo -e "${RED}Error: Server failed to start within ${MAX_WAIT} seconds${NC}"
    exit 1
fi

# Change back to docs directory
cd - > /dev/null

# Create static directory if it doesn't exist
mkdir -p "$(dirname "$OPENAPI_OUTPUT")"

# Fetch the OpenAPI specification
echo -e "${YELLOW}Fetching OpenAPI specification...${NC}"
if curl -s "http://localhost:${SERVER_PORT}/openapi.json" -o "$OPENAPI_OUTPUT"; then
    echo -e "${GREEN}✓ OpenAPI specification saved to $OPENAPI_OUTPUT${NC}"

    # Validate JSON
    if command -v jq &> /dev/null; then
        if jq empty "$OPENAPI_OUTPUT" 2>/dev/null; then
            echo -e "${GREEN}✓ OpenAPI specification is valid JSON${NC}"
            # Pretty print the JSON
            jq . "$OPENAPI_OUTPUT" > "${OPENAPI_OUTPUT}.tmp" && mv "${OPENAPI_OUTPUT}.tmp" "$OPENAPI_OUTPUT"
        else
            echo -e "${RED}Error: Invalid JSON in OpenAPI specification${NC}"
            exit 1
        fi
    fi
else
    echo -e "${RED}Error: Failed to fetch OpenAPI specification${NC}"
    exit 1
fi

echo -e "${GREEN}✅ OpenAPI specification successfully fetched!${NC}"