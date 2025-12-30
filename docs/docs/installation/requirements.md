---
sidebar_position: 2
title: System Requirements
---

# System Requirements

This page lists hardware and software requirements. For the complete deployment guide, see [Deployment Guide](./overview).

## Server Requirements

### Minimum Requirements

- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **OS**: Ubuntu 22.04+ or compatible Linux
- **Network**: Public IP address

### Recommended Requirements

- **CPU**: 8+ cores
- **RAM**: 16 GB
- **Storage**: 100 GB SSD
- **Network**: 1 Gbps connection

## Software Requirements

- Docker Engine 20.10+
- Docker Compose 2.0+

## External Services

### Required

- **Two domain names** - One for frontend (e.g., `app.example.com`), one for API (e.g., `api.example.com`)
- **Modal.com account** - For GPU-accelerated transcription and diarization (free tier available)
- **HuggingFace account** - For Pyannote diarization model access
- **LLM API** - For generating summaries and topic detection. Options:
  - OpenAI API (https://platform.openai.com/account/api-keys)
  - Any OpenAI-compatible endpoint (vLLM, LiteLLM, Ollama)
  - Self-hosted: Phi-4 14B 4-bit recommended (~8GB VRAM)

### Required for Live Meeting Rooms

- **Daily.co account** - For video conferencing (free tier available at https://dashboard.daily.co)
- **AWS S3 bucket + IAM Role** - For Daily.co to store recordings
- **Another AWS S3 bucket (optional, can reuse the one above)** - For Reflector to store "compiled" mp3 files and transient diarization process temporary files

### Optional

- **AWS S3** - For cloud storage of recordings and transcripts
- **Authentik** - For SSO/OIDC authentication
- **Sentry** - For error tracking

## Development Requirements

For local development only (not required for production deployment):

- Node.js 22+ (for frontend development)
- Python 3.12+ (for backend development)
- pnpm (for frontend package management)
- uv (for Python package management)
