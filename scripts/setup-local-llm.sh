#!/usr/bin/env bash
set -euo pipefail

MODEL="${LLM_MODEL:-qwen2.5:14b}"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

wait_for_ollama() {
    local url="$1"
    local retries=30
    for i in $(seq 1 "$retries"); do
        if curl -sf "$url/api/tags" > /dev/null 2>&1; then
            return 0
        fi
        echo "  Waiting for Ollama... ($i/$retries)"
        sleep 2
    done
    echo "ERROR: Ollama not responding at $url after $retries attempts"
    return 1
}

OS="$(uname -s)"

case "$OS" in
    Darwin)
        echo "macOS detected -- Ollama must run natively for Metal GPU acceleration."
        echo ""

        if ! command -v ollama &> /dev/null; then
            echo "Ollama not found. Install it first:"
            echo "  brew install ollama"
            echo "  # or download from https://ollama.com/download"
            exit 1
        fi

        # Start Ollama if not already running
        if ! curl -sf "http://localhost:$OLLAMA_PORT/api/tags" > /dev/null 2>&1; then
            echo "Starting Ollama..."
            ollama serve &
            disown
        else
            echo "Ollama already running."
        fi

        wait_for_ollama "http://localhost:$OLLAMA_PORT"

        echo "Pulling model $MODEL..."
        ollama pull "$MODEL"

        echo ""
        echo "Done. Add to server/.env:"
        echo "  LLM_URL=http://host.docker.internal:$OLLAMA_PORT/v1"
        echo "  LLM_MODEL=$MODEL"
        echo "  LLM_API_KEY=not-needed"
        echo ""
        echo "Then: docker compose up -d"
        ;;

    Linux)
        echo "Linux detected."
        echo ""

        if command -v nvidia-smi &> /dev/null && nvidia-smi > /dev/null 2>&1; then
            echo "NVIDIA GPU detected -- using ollama-gpu profile."
            PROFILE="ollama-gpu"
            LLM_URL="http://ollama:$OLLAMA_PORT/v1"
        else
            echo "No NVIDIA GPU -- using ollama-cpu profile."
            PROFILE="ollama-cpu"
            LLM_URL="http://ollama-cpu:$OLLAMA_PORT/v1"
        fi

        COMPOSE="docker compose -f docker-compose.yml -f docker-compose.standalone.yml"

        echo "Starting Ollama container..."
        $COMPOSE --profile "$PROFILE" up -d

        # Determine container name
        if [ "$PROFILE" = "ollama-gpu" ]; then
            SVC="ollama"
        else
            SVC="ollama-cpu"
        fi

        wait_for_ollama "http://localhost:$OLLAMA_PORT"

        echo "Pulling model $MODEL..."
        $COMPOSE exec "$SVC" ollama pull "$MODEL"

        echo ""
        echo "Done. Add to server/.env:"
        echo "  LLM_URL=$LLM_URL"
        echo "  LLM_MODEL=$MODEL"
        echo "  LLM_API_KEY=not-needed"
        echo ""
        echo "Then: $COMPOSE --profile $PROFILE up -d"
        ;;

    *)
        echo "Unsupported OS: $OS"
        exit 1
        ;;
esac
