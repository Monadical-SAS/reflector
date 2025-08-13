# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Reflector is an AI-powered audio transcription and meeting analysis platform with real-time processing capabilities. The system consists of:

- **Frontend**: Next.js 14 React application (`www/`) with Chakra UI, real-time WebSocket integration
- **Backend**: Python FastAPI server (`server/`) with async database operations and background processing
- **Processing**: GPU-accelerated ML pipeline for transcription, diarization, summarization via Modal.com
- **Infrastructure**: Redis, PostgreSQL/SQLite, Celery workers, WebRTC streaming

## Development Commands

### Backend (Python) - `cd server/`

**Setup and Dependencies:**
```bash
# Install dependencies
uv sync

# Database migrations (first run or schema changes)
uv run alembic upgrade head

# Start services
docker compose up -d redis
```

**Development:**
```bash
# Start FastAPI server
uv run -m reflector.app --reload

# Start Celery worker for background tasks
uv run celery -A reflector.worker.app worker --loglevel=info

# Start Celery beat scheduler (optional, for cron jobs)
uv run celery -A reflector.worker.app beat
```

**Testing:**
```bash
# Run all tests with coverage
uv run pytest

# Run specific test file
uv run pytest tests/test_transcripts.py

# Run tests with verbose output
uv run pytest -v
```

**Process Audio Files:**
```bash
# Process local audio file manually
uv run python -m reflector.tools.process path/to/audio.wav
```

### Frontend (Next.js) - `cd www/`

**Setup:**
```bash
# Install dependencies
pnpm install

# Copy configuration templates
cp .env_template .env
cp config-template.ts config.ts
```

**Development:**
```bash
# Start development server
pnpm dev

# Generate TypeScript API client from OpenAPI spec
pnpm openapi

# Lint code
pnpm lint

# Format code
pnpm format

# Build for production
pnpm build
```

### Docker Compose (Full Stack)

```bash
# Start all services
docker compose up -d

# Start specific services
docker compose up -d redis server worker
```

## Architecture Overview

### Backend Processing Pipeline

The audio processing follows a modular pipeline architecture:

1. **Audio Input**: WebRTC streaming, file upload, or cloud recording ingestion
2. **Chunking**: Audio split into processable segments (`AudioChunkerProcessor`)
3. **Transcription**: Whisper or Modal.com GPU processing (`AudioTranscriptAutoProcessor`)
4. **Diarization**: Speaker identification (`AudioDiarizationAutoProcessor`)
5. **Text Processing**: Formatting, translation, topic detection
6. **Summarization**: AI-powered summaries and title generation
7. **Storage**: Database persistence with optional S3 backend

### Database Models

Core entities:
- `transcript`: Main table with processing results, summaries, topics, participants
- `meeting`: Live meeting sessions with consent management
- `room`: Virtual meeting spaces with configuration
- `recording`: Audio/video file metadata and processing status

### API Structure

All endpoints prefixed `/v1/`:
- `transcripts/` - CRUD operations for transcripts
- `transcripts_audio/` - Audio streaming and download
- `transcripts_webrtc/` - Real-time WebRTC endpoints
- `transcripts_websocket/` - WebSocket for live updates
- `meetings/` - Meeting lifecycle management
- `rooms/` - Virtual room management

### Frontend Architecture

- **App Router**: Next.js 14 with route groups for organization
- **State**: React Context pattern, no Redux
- **Real-time**: WebSocket integration for live transcription updates
- **Auth**: NextAuth.js with Authentik OAuth/OIDC provider
- **UI**: Chakra UI components with Tailwind CSS utilities

## Key Configuration

### Environment Variables

**Backend** (`server/.env`):
- `DATABASE_URL` - Database connection string
- `REDIS_URL` - Redis broker for Celery
- `TRANSCRIPT_BACKEND=modal` + `TRANSCRIPT_MODAL_API_KEY` - Modal.com transcription
- `DIARIZATION_BACKEND=modal` + `DIARIZATION_MODAL_API_KEY` - Modal.com diarization
- `TRANSLATION_BACKEND=modal` + `TRANSLATION_MODAL_API_KEY` - Modal.com translation
- `WHEREBY_API_KEY` - Video platform integration
- `REFLECTOR_AUTH_BACKEND` - Authentication method (none, jwt)

**Frontend** (`www/.env`):
- `NEXTAUTH_URL`, `NEXTAUTH_SECRET` - Authentication configuration
- `NEXT_PUBLIC_REFLECTOR_API_URL` - Backend API endpoint
- `REFLECTOR_DOMAIN_CONFIG` - Feature flags and domain settings

## Testing Strategy

- **Backend**: pytest with async support, HTTP client mocking, audio processing tests
- **Frontend**: No current test suite - opportunities for Jest/React Testing Library
- **Coverage**: Backend maintains test coverage reports in `htmlcov/`

## GPU Processing

Modal.com integration for scalable ML processing:
- Deploy changes: `modal run server/gpu/path/to/model.py`
- Requires Modal account with `REFLECTOR_GPU_APIKEY` secret
- Fallback to local processing when Modal unavailable

## Common Issues

- **Permissions**: Browser microphone access required in System Preferences
- **Audio Routing**: Use BlackHole (Mac) for merging multiple audio sources
- **WebRTC**: Ensure proper CORS configuration for cross-origin streaming
- **Database**: Run `uv run alembic upgrade head` after pulling schema changes

## Pipeline/worker related info

If you need to do any worker/pipeline related work, search for "Pipeline" classes and their "create" or "build" methods to find the main processor sequence. Look for task orchestration patterns (like "chord", "group", or "chain") to identify the post-processing flow with parallel execution chains. This will give you abstract vision on how processing pipeling is organized.
