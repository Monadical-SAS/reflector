#!/bin/bash
set -e

# --- Usage ---
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --hf-token TOKEN    HuggingFace token for Pyannote model"
    echo "  --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                              # Interactive mode"
    echo "  $0 --hf-token hf_xxxxx          # Non-interactive mode"
    echo ""
    exit 0
}

# --- Parse Arguments ---
HF_TOKEN=""
while [[ $# -gt 0 ]]; do
    case $1 in
        --hf-token)
            HF_TOKEN="$2"
            shift 2
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

echo "=========================================="
echo "Reflector GPU Functions Deployment"
echo "=========================================="
echo ""

# --- Check Dependencies ---
if ! command -v modal &> /dev/null; then
    echo "Error: Modal CLI not installed."
    echo "  Install with: pip install modal"
    exit 1
fi

if ! command -v openssl &> /dev/null; then
    echo "Error: openssl not found."
    echo "  Mac: brew install openssl"
    echo "  Ubuntu: sudo apt-get install openssl"
    exit 1
fi

# Check Modal authentication
if ! modal profile current &> /dev/null; then
    echo "Error: Not authenticated with Modal."
    echo "  Run: modal setup"
    exit 1
fi

# --- HuggingFace Token Setup ---
if [ -z "$HF_TOKEN" ]; then
    echo "HuggingFace token required for Pyannote diarization model."
    echo "1. Create account at https://huggingface.co"
    echo "2. Accept license at https://huggingface.co/pyannote/speaker-diarization-3.1"
    echo "3. Generate token at https://huggingface.co/settings/tokens"
    echo ""
    read -p "Enter your HuggingFace token: " HF_TOKEN
fi

if [ -z "$HF_TOKEN" ]; then
    echo "Error: HuggingFace token is required for diarization"
    exit 1
fi

# Basic token format validation
if [[ ! "$HF_TOKEN" =~ ^hf_ ]]; then
    echo "Warning: HuggingFace tokens usually start with 'hf_'"
    if [ -t 0 ]; then
        read -p "Continue anyway? (y/n): " confirm
        if [ "$confirm" != "y" ]; then
            exit 1
        fi
    else
        echo "Non-interactive mode: proceeding anyway"
    fi
fi

# --- Auto-generate API Key ---
echo ""
echo "Generating API key for GPU services..."
API_KEY=$(openssl rand -hex 32)

# --- Create Modal Secrets ---
echo "Creating Modal secrets..."

# Create or update hf_token secret (delete first if exists)
if modal secret list 2>/dev/null | grep -q "hf_token"; then
    echo "  -> Recreating secret: hf_token"
    modal secret delete hf_token --yes 2>/dev/null || true
fi
echo "  -> Creating secret: hf_token"
modal secret create hf_token HF_TOKEN="$HF_TOKEN"

# Create or update reflector-gpu secret (delete first if exists)
if modal secret list 2>/dev/null | grep -q "reflector-gpu"; then
    echo "  -> Recreating secret: reflector-gpu"
    modal secret delete reflector-gpu --yes 2>/dev/null || true
fi
echo "  -> Creating secret: reflector-gpu"
modal secret create reflector-gpu REFLECTOR_GPU_APIKEY="$API_KEY"

# --- Deploy Functions ---
echo ""
echo "Deploying transcriber (Whisper)..."
TRANSCRIBER_URL=$(modal deploy reflector_transcriber.py 2>&1 | grep -o 'https://[^ ]*web.modal.run' | head -1)
if [ -z "$TRANSCRIBER_URL" ]; then
    echo "Error: Failed to deploy transcriber. Check Modal dashboard for details."
    exit 1
fi
echo "  -> $TRANSCRIBER_URL"

echo ""
echo "Deploying diarizer (Pyannote)..."
DIARIZER_URL=$(modal deploy reflector_diarizer.py 2>&1 | grep -o 'https://[^ ]*web.modal.run' | head -1)
if [ -z "$DIARIZER_URL" ]; then
    echo "Error: Failed to deploy diarizer. Check Modal dashboard for details."
    exit 1
fi
echo "  -> $DIARIZER_URL"

# --- Output Configuration ---
echo ""
echo "=========================================="
echo "Deployment complete!"
echo "=========================================="
echo ""
echo "Copy these values to your server's server/.env file:"
echo ""
echo "# --- Modal GPU Configuration ---"
echo "TRANSCRIPT_BACKEND=modal"
echo "TRANSCRIPT_URL=$TRANSCRIBER_URL"
echo "TRANSCRIPT_MODAL_API_KEY=$API_KEY"
echo ""
echo "DIARIZATION_BACKEND=modal"
echo "DIARIZATION_URL=$DIARIZER_URL"
echo "DIARIZATION_MODAL_API_KEY=$API_KEY"
echo "# --- End Modal Configuration ---"
