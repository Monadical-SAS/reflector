#!/usr/bin/env bash
#
# Standalone local development setup for Reflector.
# Takes a fresh clone to a working instance — no cloud accounts, no API keys.
#
# Usage:
#   ./scripts/setup-standalone.sh
#
# Idempotent — safe to re-run at any time.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

SERVER_ENV="$ROOT_DIR/server/.env"
WWW_ENV="$ROOT_DIR/www/.env.local"

MODEL="${LLM_MODEL:-qwen2.5:14b}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

OS="$(uname -s)"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}==>${NC} $*"; }
ok()    { echo -e "${GREEN}  ✓${NC} $*"; }
warn()  { echo -e "${YELLOW}  !${NC} $*"; }
err()   { echo -e "${RED}  ✗${NC} $*" >&2; }

# --- Helpers ---

dump_diagnostics() {
    local failed_svc="${1:-}"
    echo ""
    err "========== DIAGNOSTICS =========="

    err "Container status:"
    compose_cmd ps -a --format "table {{.Name}}\t{{.Status}}" 2>/dev/null || true
    echo ""

    # Show logs for any container that exited
    local stopped
    stopped=$(compose_cmd ps -a --format '{{.Name}}\t{{.Status}}' 2>/dev/null \
        | grep -iv 'up\|running' | awk -F'\t' '{print $1}' || true)
    for c in $stopped; do
        err "--- Logs for $c (exited/unhealthy) ---"
        docker logs --tail 30 "$c" 2>&1 || true
        echo ""
    done

    # If a specific service failed, always show its logs
    if [[ -n "$failed_svc" ]]; then
        err "--- Logs for $failed_svc (last 40) ---"
        compose_cmd logs "$failed_svc" --tail 40 2>&1 || true
        echo ""
        # Try health check from inside the container as extra signal
        err "--- Internal health check ($failed_svc) ---"
        compose_cmd exec -T "$failed_svc" \
            curl -sf http://localhost:1250/health 2>&1 || echo "(not reachable internally either)"
    fi

    err "================================="
}

trap 'dump_diagnostics' ERR

# Get the image ID for a compose service (works even when containers are not running).
svc_image_id() {
    local svc="$1"
    # Extract image name from compose config YAML, fall back to <project>-<service>
    local img_name
    img_name=$(compose_cmd config 2>/dev/null \
        | sed -n "/^  ${svc}:/,/^  [a-z]/p" | grep '^\s*image:' | awk '{print $2}')
    img_name="${img_name:-reflector-$svc}"
    docker images -q "$img_name" 2>/dev/null | head -1
}

# Ensure images with build contexts are up-to-date.
# Docker layer cache makes this fast (~seconds) when source hasn't changed.
rebuild_images() {
    local svc
    for svc in web cpu; do
        local old_id
        old_id=$(svc_image_id "$svc")
        old_id="${old_id:-<none>}"

        info "Building $svc..."
        compose_cmd build "$svc"

        local new_id
        new_id=$(svc_image_id "$svc")

        if [[ "$old_id" == "$new_id" ]]; then
            ok "$svc unchanged (${new_id:0:12})"
        else
            ok "$svc rebuilt (${old_id:0:12} -> ${new_id:0:12})"
        fi
    done
}

wait_for_url() {
    local url="$1" label="$2" retries="${3:-30}" interval="${4:-2}"
    for i in $(seq 1 "$retries"); do
        if curl -sf "$url" > /dev/null 2>&1; then
            return 0
        fi
        echo -ne "\r  Waiting for $label... ($i/$retries)"
        sleep "$interval"
    done
    echo ""
    err "$label not responding at $url after $retries attempts"
    return 1
}

env_has_key() {
    local file="$1" key="$2"
    grep -q "^${key}=" "$file" 2>/dev/null
}

env_set() {
    local file="$1" key="$2" value="$3"
    if env_has_key "$file" "$key"; then
        # Replace existing value (portable sed)
        if [[ "$OS" == "Darwin" ]]; then
            sed -i '' "s|^${key}=.*|${key}=${value}|" "$file"
        else
            sed -i "s|^${key}=.*|${key}=${value}|" "$file"
        fi
    else
        echo "${key}=${value}" >> "$file"
    fi
}

resolve_symlink() {
    local file="$1"
    if [[ -L "$file" ]]; then
        warn "$(basename "$file") is a symlink — creating standalone copy"
        cp -L "$file" "$file.tmp"
        rm "$file"
        mv "$file.tmp" "$file"
    fi
}

compose_cmd() {
    local compose_files="-f $ROOT_DIR/docker-compose.yml -f $ROOT_DIR/docker-compose.standalone.yml"
    if [[ "$OS" == "Linux" ]] && [[ -n "${OLLAMA_PROFILE:-}" ]]; then
        docker compose $compose_files --profile "$OLLAMA_PROFILE" "$@"
    else
        docker compose $compose_files "$@"
    fi
}

# =========================================================
# Step 1: LLM / Ollama
# =========================================================
step_llm() {
    info "Step 1: LLM setup (Ollama + $MODEL)"

    case "$OS" in
        Darwin)
            if ! command -v ollama &> /dev/null; then
                err "Ollama not found. Install it:"
                err "  brew install ollama"
                err "  # or https://ollama.com/download"
                exit 1
            fi

            # Start if not running
            if ! curl -sf "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
                info "Starting Ollama..."
                ollama serve &
                disown
            fi

            wait_for_url "http://localhost:$OLLAMA_PORT/api/tags" "Ollama"
            echo ""

            # Pull model if not already present
            if ollama list 2>/dev/null | awk '{print $1}' | grep -qxF "$MODEL"; then
                ok "Model $MODEL already pulled"
            else
                info "Pulling model $MODEL (this may take a while)..."
                ollama pull "$MODEL"
            fi

            LLM_URL_VALUE="http://host.docker.internal:$OLLAMA_PORT/v1"
            ;;

        Linux)
            if command -v nvidia-smi &> /dev/null && nvidia-smi > /dev/null 2>&1; then
                ok "NVIDIA GPU detected — using ollama-gpu profile"
                OLLAMA_PROFILE="ollama-gpu"
                OLLAMA_SVC="ollama"
                LLM_URL_VALUE="http://ollama:$OLLAMA_PORT/v1"
            else
                warn "No NVIDIA GPU — using ollama-cpu profile"
                OLLAMA_PROFILE="ollama-cpu"
                OLLAMA_SVC="ollama-cpu"
                LLM_URL_VALUE="http://ollama-cpu:$OLLAMA_PORT/v1"
            fi

            info "Starting Ollama container..."
            compose_cmd up -d

            wait_for_url "http://localhost:$OLLAMA_PORT/api/tags" "Ollama"
            echo ""

            # Pull model inside container
            if compose_cmd exec "$OLLAMA_SVC" ollama list 2>/dev/null | awk '{print $1}' | grep -qxF "$MODEL"; then
                ok "Model $MODEL already pulled"
            else
                info "Pulling model $MODEL inside container (this may take a while)..."
                compose_cmd exec "$OLLAMA_SVC" ollama pull "$MODEL"
            fi
            ;;

        *)
            err "Unsupported OS: $OS"
            exit 1
            ;;
    esac

    ok "LLM ready ($MODEL via Ollama)"
}

# =========================================================
# Step 2: Generate server/.env
# =========================================================
step_server_env() {
    info "Step 2: Generating server/.env"

    resolve_symlink "$SERVER_ENV"

    if [[ -f "$SERVER_ENV" ]]; then
        ok "server/.env already exists — ensuring standalone vars"
    else
        cat > "$SERVER_ENV" << 'ENVEOF'
# Generated by setup-standalone.sh — standalone local development
# Source of truth for settings: server/reflector/settings.py
ENVEOF
        ok "Created server/.env"
    fi

    # Ensure all standalone-critical vars (appends if missing, replaces if present)
    env_set "$SERVER_ENV" "DATABASE_URL" "postgresql+asyncpg://reflector:reflector@postgres:5432/reflector"
    env_set "$SERVER_ENV" "REDIS_HOST" "redis"
    env_set "$SERVER_ENV" "CELERY_BROKER_URL" "redis://redis:6379/1"
    env_set "$SERVER_ENV" "CELERY_RESULT_BACKEND" "redis://redis:6379/1"
    env_set "$SERVER_ENV" "AUTH_BACKEND" "none"
    env_set "$SERVER_ENV" "PUBLIC_MODE" "true"
    # TRANSCRIPT_BACKEND, TRANSCRIPT_URL, DIARIZATION_BACKEND, DIARIZATION_URL
    # are set via docker-compose.standalone.yml `environment:` overrides — not written here
    # so we don't clobber the user's server/.env for non-standalone use.
    env_set "$SERVER_ENV" "TRANSLATION_BACKEND" "passthrough"
    env_set "$SERVER_ENV" "LLM_URL" "$LLM_URL_VALUE"
    env_set "$SERVER_ENV" "LLM_MODEL" "$MODEL"
    env_set "$SERVER_ENV" "LLM_API_KEY" "not-needed"

    ok "Standalone vars set (LLM_URL=$LLM_URL_VALUE)"
}

# =========================================================
# Step 3: Object storage (Garage)
# =========================================================
step_storage() {
    info "Step 3: Object storage (Garage)"

    # Generate garage.toml from template (fill in RPC secret)
    GARAGE_TOML="$ROOT_DIR/scripts/garage.toml"
    GARAGE_TOML_RUNTIME="$ROOT_DIR/data/garage.toml"
    if [[ ! -f "$GARAGE_TOML_RUNTIME" ]]; then
        mkdir -p "$ROOT_DIR/data"
        RPC_SECRET=$(openssl rand -hex 32)
        sed "s|__GARAGE_RPC_SECRET__|${RPC_SECRET}|" "$GARAGE_TOML" > "$GARAGE_TOML_RUNTIME"
    fi

    compose_cmd up -d garage

    wait_for_url "http://localhost:3903/health" "Garage admin API"
    echo ""

    # Layout: get node ID, assign, apply (skip if already applied)
    NODE_ID=$(compose_cmd exec -T garage /garage node id -q 2>/dev/null | tr -d '[:space:]')
    LAYOUT_STATUS=$(compose_cmd exec -T garage /garage layout show 2>&1 || true)
    if echo "$LAYOUT_STATUS" | grep -q "No nodes"; then
        compose_cmd exec -T garage /garage layout assign "$NODE_ID" -c 1G -z dc1
        compose_cmd exec -T garage /garage layout apply --version 1
    fi

    # Create bucket (idempotent — skip if exists)
    if ! compose_cmd exec -T garage /garage bucket info reflector-media &>/dev/null; then
        compose_cmd exec -T garage /garage bucket create reflector-media
    fi

    # Create key (idempotent — skip if exists)
    CREATED_KEY=false
    if compose_cmd exec -T garage /garage key info reflector &>/dev/null; then
        ok "Key 'reflector' already exists"
    else
        KEY_OUTPUT=$(compose_cmd exec -T garage /garage key create reflector)
        CREATED_KEY=true
    fi

    # Grant bucket permissions (idempotent)
    compose_cmd exec -T garage /garage bucket allow reflector-media --read --write --key reflector

    # Set env vars (only parse key on first create — key info redacts the secret)
    env_set "$SERVER_ENV" "TRANSCRIPT_STORAGE_BACKEND" "aws"
    env_set "$SERVER_ENV" "TRANSCRIPT_STORAGE_AWS_ENDPOINT_URL" "http://garage:3900"
    env_set "$SERVER_ENV" "TRANSCRIPT_STORAGE_AWS_BUCKET_NAME" "reflector-media"
    env_set "$SERVER_ENV" "TRANSCRIPT_STORAGE_AWS_REGION" "garage"
    if [[ "$CREATED_KEY" == "true" ]]; then
        KEY_ID=$(echo "$KEY_OUTPUT" | grep -i "key id" | awk '{print $NF}')
        KEY_SECRET=$(echo "$KEY_OUTPUT" | grep -i "secret key" | awk '{print $NF}')
        env_set "$SERVER_ENV" "TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID" "$KEY_ID"
        env_set "$SERVER_ENV" "TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY" "$KEY_SECRET"
    fi

    ok "Object storage ready (Garage)"
}

# =========================================================
# Step 4: Generate www/.env.local
# =========================================================
step_www_env() {
    info "Step 4: Generating www/.env.local"

    resolve_symlink "$WWW_ENV"

    if [[ -f "$WWW_ENV" ]]; then
        ok "www/.env.local already exists — ensuring standalone vars"
    else
        cat > "$WWW_ENV" << 'ENVEOF'
# Generated by setup-standalone.sh — standalone local development
ENVEOF
        ok "Created www/.env.local"
    fi

    env_set "$WWW_ENV" "SITE_URL" "http://localhost:3000"
    env_set "$WWW_ENV" "NEXTAUTH_URL" "http://localhost:3000"
    env_set "$WWW_ENV" "NEXTAUTH_SECRET" "standalone-dev-secret-not-for-production"
    env_set "$WWW_ENV" "API_URL" "http://localhost:1250"
    env_set "$WWW_ENV" "WEBSOCKET_URL" "ws://localhost:1250"
    env_set "$WWW_ENV" "SERVER_API_URL" "http://server:1250"
    env_set "$WWW_ENV" "FEATURE_REQUIRE_LOGIN" "false"

    ok "Standalone www vars set"
}

# =========================================================
# Step 5: Start all services
# =========================================================
step_services() {
    info "Step 5: Starting Docker services"

    # Check for port conflicts — stale processes silently shadow Docker port mappings.
    # OrbStack/Docker Desktop bind ports for forwarding; ignore those PIDs.
    local ports_ok=true
    for port in 3000 1250 5432 6379 3900 3903; do
        local pids
        pids=$(lsof -ti :"$port" 2>/dev/null || true)
        for pid in $pids; do
            local pname
            pname=$(ps -p "$pid" -o comm= 2>/dev/null || true)
            # OrbStack and Docker Desktop own port forwarding — not real conflicts
            if [[ "$pname" == *"OrbStack"* ]] || [[ "$pname" == *"com.docker"* ]] || [[ "$pname" == *"vpnkit"* ]]; then
                continue
            fi
            warn "Port $port already in use by PID $pid ($pname)"
            warn "Kill it with: lsof -ti :$port | xargs kill"
            ports_ok=false
        done
    done
    if [[ "$ports_ok" == "false" ]]; then
        warn "Port conflicts detected — Docker containers may not be reachable"
        warn "Continuing anyway (services will start but may be shadowed)"
    fi

    # Rebuild images if source has changed (Docker layer cache makes this fast when unchanged)
    rebuild_images

    # server runs alembic migrations on startup automatically (see runserver.sh)
    compose_cmd up -d postgres redis garage cpu server worker beat web
    ok "Containers started"

    # Quick sanity check — catch containers that exit immediately (bad image, missing file, etc.)
    sleep 3
    local exited
    exited=$(compose_cmd ps -a --format '{{.Name}} {{.Status}}' 2>/dev/null \
        | grep -i 'exit' || true)
    if [[ -n "$exited" ]]; then
        warn "Some containers exited immediately:"
        echo "$exited" | while read -r line; do warn "  $line"; done
        dump_diagnostics
    fi

    info "Server is running migrations (alembic upgrade head)..."
}

# =========================================================
# Step 6: Health checks
# =========================================================
step_health() {
    info "Step 6: Health checks"

    # CPU service may take a while on first start (model download + load).
    # No host port exposed — check via docker exec.
    info "Waiting for CPU service (first start downloads ~1GB of models)..."
    local cpu_ok=false
    for i in $(seq 1 120); do
        if compose_cmd exec -T cpu curl -sf http://localhost:8000/docs > /dev/null 2>&1; then
            cpu_ok=true
            break
        fi
        echo -ne "\r  Waiting for CPU service... ($i/120)"
        sleep 5
    done
    echo ""
    if [[ "$cpu_ok" == "true" ]]; then
        ok "CPU service healthy (transcription + diarization)"
    else
        warn "CPU service not ready yet — it will keep loading in the background"
        warn "Check with: docker compose logs cpu"
    fi

    # Server may take a long time on first run — alembic migrations run before uvicorn starts.
    # Use docker exec so this works regardless of network_mode or port mapping.
    info "Waiting for Server API (first run includes database migrations)..."
    local server_ok=false
    for i in $(seq 1 90); do
        # Check if container is still running
        local svc_status
        svc_status=$(compose_cmd ps server --format '{{.Status}}' 2>/dev/null || true)
        if [[ -z "$svc_status" ]] || echo "$svc_status" | grep -qi 'exit'; then
            echo ""
            err "Server container exited unexpectedly"
            dump_diagnostics server
            exit 1
        fi
        # Health check from inside container (avoids host networking issues)
        if compose_cmd exec -T server curl -sf http://localhost:1250/health > /dev/null 2>&1; then
            server_ok=true
            break
        fi
        echo -ne "\r  Waiting for Server API... ($i/90)"
        sleep 5
    done
    echo ""
    if [[ "$server_ok" == "true" ]]; then
        ok "Server API healthy"
    else
        err "Server API not ready after ~7 minutes"
        dump_diagnostics server
        exit 1
    fi

    wait_for_url "http://localhost:3000" "Frontend" 90 3
    echo ""
    ok "Frontend responding"

    # Check LLM reachability from inside a container
    if compose_cmd exec -T server \
        curl -sf "$LLM_URL_VALUE/models" > /dev/null 2>&1; then
        ok "LLM reachable from containers"
    else
        warn "LLM not reachable from containers at $LLM_URL_VALUE"
        warn "Summaries/topics/titles won't work until LLM is accessible"
    fi
}

# =========================================================
# Main
# =========================================================
main() {
    echo ""
    echo "=========================================="
    echo " Reflector — Standalone Local Setup"
    echo "=========================================="
    echo ""

    # Ensure we're in the repo root
    if [[ ! -f "$ROOT_DIR/docker-compose.yml" ]]; then
        err "docker-compose.yml not found in $ROOT_DIR"
        err "Run this script from the repo root: ./scripts/setup-standalone.sh"
        exit 1
    fi


    # LLM_URL_VALUE is set by step_llm, used by later steps
    LLM_URL_VALUE=""
    OLLAMA_PROFILE=""

    # docker-compose.yml may reference env_files that don't exist yet;
    # touch them so compose_cmd works before the steps that populate them.
    touch "$SERVER_ENV" "$WWW_ENV"

    step_llm
    echo ""
    step_server_env
    echo ""
    step_storage
    echo ""
    step_www_env
    echo ""
    step_services
    echo ""
    step_health

    echo ""
    echo "=========================================="
    echo -e " ${GREEN}Reflector is running!${NC}"
    echo "=========================================="
    echo ""
    echo "  Frontend:  http://localhost:3000"
    echo "  API:       http://localhost:1250"
    echo ""
    echo "  To stop:   docker compose down"
    echo "  To re-run: ./scripts/setup-standalone.sh"
    echo ""
}

main "$@"
