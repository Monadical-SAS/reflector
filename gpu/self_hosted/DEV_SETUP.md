# Local Development GPU Setup

Run transcription and diarization locally for development/testing.

> **For production deployment**, see the [Self-Hosted GPU Setup Guide](../../docs/docs/installation/self-hosted-gpu-setup.md).

## Prerequisites

1. **Python 3.12+** and **uv** package manager
2. **FFmpeg** installed and on PATH
3. **HuggingFace account** with access to pyannote models

### Accept Pyannote Licenses (Required)

Before first run, accept licenses for these gated models (logged into HuggingFace):
- https://hf.co/pyannote/speaker-diarization-3.1
- https://hf.co/pyannote/segmentation-3.0

## Quick Start

### 1. Install dependencies

```bash
cd gpu/self_hosted
uv sync
```

### 2. Start the GPU service

```bash
cd gpu/self_hosted
HF_TOKEN=<your-huggingface-token> \
REFLECTOR_GPU_APIKEY=dev-key-12345 \
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

Note: The `.env` file is NOT auto-loaded. Pass env vars explicitly or use:
```bash
export HF_TOKEN=<your-token>
export REFLECTOR_GPU_APIKEY=dev-key-12345
.venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

### 3. Configure Reflector to use local GPU

Edit `server/.env`:

```bash
# Transcription - local GPU service
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=http://host.docker.internal:8000
TRANSCRIPT_MODAL_API_KEY=dev-key-12345

# Diarization - local GPU service
DIARIZATION_BACKEND=modal
DIARIZATION_URL=http://host.docker.internal:8000
DIARIZATION_MODAL_API_KEY=dev-key-12345
```

Note: Use `host.docker.internal` because Reflector server runs in Docker.

### 4. Restart Reflector server

```bash
cd server
docker compose restart server worker
```

## Testing

### Test transcription

```bash
curl -s -X POST http://localhost:8000/v1/audio/transcriptions \
  -H "Authorization: Bearer dev-key-12345" \
  -F "file=@/path/to/audio.wav" \
  -F "language=en"
```

### Test diarization

```bash
curl -s -X POST "http://localhost:8000/diarize?audio_file_url=<audio-url>" \
  -H "Authorization: Bearer dev-key-12345"
```

## Platform Notes

### macOS (ARM)

Docker build fails - CUDA packages are x86_64 only. Use local Python instead:
```bash
uv sync
HF_TOKEN=xxx REFLECTOR_GPU_APIKEY=xxx .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
```

### Linux with NVIDIA GPU

Docker works with CUDA acceleration:
```bash
docker compose up -d
```

### CPU-only

Works on any platform, just slower. PyTorch auto-detects and falls back to CPU.

## Switching Back to Modal.com

Edit `server/.env`:

```bash
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://monadical-sas--reflector-transcriber-parakeet-web.modal.run
TRANSCRIPT_MODAL_API_KEY=<modal-api-key>

DIARIZATION_BACKEND=modal
DIARIZATION_URL=https://monadical-sas--reflector-diarizer-web.modal.run
DIARIZATION_MODAL_API_KEY=<modal-api-key>
```

## Troubleshooting

### "Could not download pyannote pipeline"
- Accept model licenses at HuggingFace (see Prerequisites)
- Verify HF_TOKEN is set and valid

### Service won't start
- Check port 8000 is free: `lsof -i :8000`
- Kill orphan processes if needed

### Transcription returns empty text
- Ensure audio contains speech (not just tones/silence)
- Check audio format is supported (wav, mp3, etc.)

### Deprecation warnings from torchaudio/pyannote
- Safe to ignore - doesn't affect functionality
