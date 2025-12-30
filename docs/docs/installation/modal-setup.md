---
sidebar_position: 4
title: Modal.com Setup
---

# Modal.com Setup

This page covers Modal.com GPU setup in detail. For the complete deployment guide, see [Deployment Guide](./overview).

Reflector uses [Modal.com](https://modal.com) for GPU-accelerated audio processing. This guide walks you through deploying the required GPU functions.

## What is Modal.com?

Modal is a serverless GPU platform. You deploy Python code that runs on their GPUs, and pay only for actual compute time. Reflector uses Modal for:

- **Transcription**: Whisper model for speech-to-text
- **Diarization**: Pyannote model for speaker identification

## Prerequisites

1. **Modal.com account** - Sign up at https://modal.com (free tier available)
2. **HuggingFace account** - Required for Pyannote diarization models:
   - Create account at https://huggingface.co
   - Accept **both** Pyannote licenses:
     - https://huggingface.co/pyannote/speaker-diarization-3.1
     - https://huggingface.co/pyannote/segmentation-3.0
   - Generate access token at https://huggingface.co/settings/tokens

## Deployment

**Location: YOUR LOCAL COMPUTER (laptop/desktop)**

Modal CLI requires browser authentication, so this must run on a machine with a browser - not on a headless server.

### Install Modal CLI

```bash
uv tool install modal
```

### Authenticate with Modal

```bash
modal setup
```

This opens your browser for authentication. Complete the login flow.

### Clone Repository and Deploy

```bash
git clone https://github.com/monadical-sas/reflector.git
cd reflector/gpu/modal_deployments
./deploy-all.sh --hf-token YOUR_HUGGINGFACE_TOKEN
```

Or run interactively (script will prompt for token):
```bash
./deploy-all.sh
```

### What the Script Does

1. **Prompts for HuggingFace token** - Needed to download the Pyannote diarization model
2. **Generates API key** - Creates a secure random key for authenticating requests to GPU functions
3. **Creates Modal secrets**:
   - `hf_token` - Your HuggingFace token
   - `reflector-gpu` - The generated API key
4. **Deploys GPU functions** - Transcriber (Whisper) and Diarizer (Pyannote)
5. **Outputs configuration** - Prints URLs and API key to console

### Example Output

```
==========================================
Reflector GPU Functions Deployment
==========================================

Generating API key for GPU services...
Creating Modal secrets...
  -> Creating secret: hf_token
  -> Creating secret: reflector-gpu

Deploying transcriber (Whisper)...
  -> https://yourname--reflector-transcriber-web.modal.run

Deploying diarizer (Pyannote)...
  -> https://yourname--reflector-diarizer-web.modal.run

==========================================
Deployment complete!
==========================================

Copy these values to your server's server/.env file:

# --- Modal GPU Configuration ---
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://yourname--reflector-transcriber-web.modal.run
TRANSCRIPT_MODAL_API_KEY=abc123...

DIARIZATION_BACKEND=modal
DIARIZATION_URL=https://yourname--reflector-diarizer-web.modal.run
DIARIZATION_MODAL_API_KEY=abc123...
# --- End Modal Configuration ---
```

Copy the output and paste it into your `server/.env` file on your server.

## Costs

Modal charges based on GPU compute time:
- Functions scale to zero when not in use (no cost when idle)
- You only pay for actual processing time
- Free tier includes $30/month of credits

Typical costs for audio processing:
- Transcription: ~$0.01-0.05 per minute of audio
- Diarization: ~$0.02-0.10 per minute of audio

## Troubleshooting

### "Modal CLI not installed"
```bash
uv tool install modal
```

### "Not authenticated with Modal"
```bash
modal setup
# Complete browser authentication
```

### "Failed to create secret hf_token"
- Verify your HuggingFace token is valid
- Ensure you've accepted the Pyannote license
- Token needs `read` permission

### Deployment fails
Check the Modal dashboard for detailed error logs:
- Visit https://modal.com/apps
- Click on the failed function
- View build and runtime logs

### Re-running deployment
The script is safe to re-run. It will:
- Update existing secrets if they exist
- Redeploy functions with latest code
- Output new configuration (API key stays the same if secret exists)

## Manual Deployment (Advanced)

If you prefer to deploy functions individually:

```bash
cd gpu/modal_deployments

# Create secrets manually
modal secret create hf_token HF_TOKEN=your-hf-token
modal secret create reflector-gpu REFLECTOR_GPU_APIKEY=$(openssl rand -hex 32)

# Deploy each function
modal deploy reflector_transcriber.py
modal deploy reflector_diarizer.py
```

## Monitoring

View your deployed functions and their usage:
- **Modal Dashboard**: https://modal.com/apps
- **Function logs**: Click on any function to view logs
- **Usage**: View compute time and costs in the dashboard
