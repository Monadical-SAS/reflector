# Self-hosted Model API

Run transcription, translation, and diarization services compatible with Reflector's GPU Model API. Works on CPU or GPU.

Environment variables

- REFLECTOR_GPU_APIKEY: Optional Bearer token. If unset, auth is disabled.
- HF_TOKEN: Optional. Required for diarization to download pyannote pipelines

Requirements

- FFmpeg must be installed and on PATH (used for URL-based and segmented transcription)
- Python 3.12+
- NVIDIA GPU optional. If available, it will be used automatically

Local run
Set env vars in self_hosted/.env file
uv sync

uv run uvicorn main:app --host 0.0.0.0 --port 8000

Authentication

- If REFLECTOR_GPU_APIKEY is set, include header: Authorization: Bearer <key>

Endpoints

- POST /v1/audio/transcriptions

  - multipart/form-data
  - fields: file (single file) OR files[] (multiple files), language, batch (true/false)
  - response: single { text, words, filename } or { results: [ ... ] }

- POST /v1/audio/transcriptions-from-url

  - application/json
  - body: { audio_file_url, language, timestamp_offset }
  - response: { text, words }

- POST /translate

  - text: query parameter
  - body (application/json): { source_language, target_language }
  - response: { text: { <src>: original, <tgt>: translated } }

- POST /diarize
  - query parameters: audio_file_url, timestamp (optional)
  - requires HF_TOKEN to be set (for pyannote)
  - response: { diarization: [ { start, end, speaker } ] }

OpenAPI docs

- Visit /docs when the server is running

Docker

- Not yet provided in this directory. A Dockerfile will be added later. For now, use Local run above

# Setup

[SETUP.md](SETUP.md)

# Conformance tests

## From this directory

TRANSCRIPT_URL=http://localhost:8000 \
TRANSCRIPT_API_KEY=dev-key \
uv run -m pytest -m model_api --no-cov ../../server/tests/test_model_api_transcript.py

TRANSLATION_URL=http://localhost:8000 \
TRANSLATION_API_KEY=dev-key \
uv run -m pytest -m model_api --no-cov ../../server/tests/test_model_api_translation.py

DIARIZATION_URL=http://localhost:8000 \
DIARIZATION_API_KEY=dev-key \
uv run -m pytest -m model_api --no-cov ../../server/tests/test_model_api_diarization.py
