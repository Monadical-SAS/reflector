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

**Linting (IMPORTANT - Run after Python changes):**
```bash
# Check only changed files without auto-fixing (must run from server/ directory)
cd server && git diff --name-only main...HEAD -- '*.py' '**/*.py' | grep -v "^migrations/versions/" | xargs ruff check --no-fix
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
yarn install

# Copy configuration templates
cp .env_template .env
cp config-template.ts config.ts
```

**Development:**
```bash
# Start development server
yarn dev

# Generate TypeScript API client from OpenAPI spec
yarn openapi

# Lint code
yarn lint

# Format code
yarn format

# Build for production
yarn build
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

## Database Migration Notes (IMPORTANT)

### SQLite vs PostgreSQL Migrations
The codebase contains migrations that were originally generated against SQLite but are used with PostgreSQL in production. These migrations contain SQLite-specific syntax that happens to be PostgreSQL-compatible:

- `REPLACE()` function works in both databases for text operations
- Boolean defaults like `sa.text("0")` are auto-converted by PostgreSQL (0→false, 1→true)
- `render_as_batch=True` in `migrations/env.py` helps abstract database differences

**DO NOT modify existing migrations** - they work correctly despite appearing SQLite-specific. If you encounter migration errors:

1. **For fresh PostgreSQL setup:**
   ```bash
   # Start containers
   docker compose up -d postgres redis server

   # Run migrations (they will work despite SQLite syntax)
   docker compose exec server uv run alembic upgrade head
   ```

2. **If migrations fail:** The issue is likely NOT the SQLite syntax. Check:
   - Database connectivity (use `localhost` for host, `postgres` for containers)
   - PostgreSQL is fully started before running migrations
   - No partial migration state from interrupted runs

3. **Alternative fresh setup (if migrations truly fail):**
   ```bash
   # Create schema directly from models
   docker compose exec server uv run python -c "from reflector.db import engine, metadata; metadata.create_all(engine)"

   # Mark all migrations as applied
   docker compose exec server uv run alembic stamp head
   ```

**Key insight:** The migrations look wrong but work correctly. PostgreSQL is forgiving enough to handle the SQLite syntax used in these migrations.

## Pipeline/worker related info

If you need to do any worker/pipeline related work, search for "Pipeline" classes and their "create" or "build" methods to find the main processor sequence. Look for task orchestration patterns (like "chord", "group", or "chain") to identify the post-processing flow with parallel execution chains. This will give you abstract vision on how processing pipeling is organized.

## CRITICAL DESIGN REVIEW MODE

Before implementing any technical requirements, you MUST act as a senior architect and:

### 1. REQUIREMENTS SANITY CHECK
Challenge requirements that seem inconsistent:
- Question contradictions between different parts of the requirements
- Identify potential confusion for future developers
- Point out semantic inconsistencies
- Consider the long-term maintainability implications

### 2. PUSH BACK CONSTRUCTIVELY
When you spot issues:
- Stop immediately before any implementation
- Explain the specific concern clearly
- Propose 2-3 solutions with trade-offs
- Wait for explicit confirmation of the approach

**REMEMBER:** Your job is to prevent future WTF moments in code review, not to blindly execute specifications. Act as the senior developer who has to maintain this code in 2 years.
