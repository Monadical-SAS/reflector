## Reflector GPU Transcription API (Specification)

This document defines the Reflector GPU transcription API that all implementations must adhere to. Current implementations include NVIDIA Parakeet (NeMo) and Whisper (faster-whisper), both deployed on Modal.com. The API surface and response shapes are OpenAI/Whisper-compatible, so clients can switch implementations by changing only the base URL.

### Base URL and Authentication

- Example base URLs (Modal web endpoints):

  - Parakeet: `https://<account>--reflector-transcriber-parakeet-web.modal.run`
  - Whisper: `https://<account>--reflector-transcriber-web.modal.run`

- All endpoints are served under `/v1` and require a Bearer token:

```
Authorization: Bearer <REFLECTOR_GPU_APIKEY>
```

Note: To switch implementations, deploy the desired variant and point `TRANSCRIPT_URL` to its base URL. The API is identical.

### Supported file types

`mp3, mp4, mpeg, mpga, m4a, wav, webm`

### Models and languages

- Parakeet (NVIDIA NeMo): default `nvidia/parakeet-tdt-0.6b-v2`
  - Language support: only `en`. Other languages return HTTP 400.
- Whisper (faster-whisper): default `large-v2` (or deployment-specific)
  - Language support: multilingual (per Whisper model capabilities).

Note: The `model` parameter is accepted by all implementations for interface parity. Some backends may treat it as informational.

### Endpoints

#### POST /v1/audio/transcriptions

Transcribe one or more uploaded audio files.

Request: multipart/form-data

- `file` (File) — optional. Single file to transcribe.
- `files` (File[]) — optional. One or more files to transcribe.
- `model` (string) — optional. Defaults to the implementation-specific model (see above).
- `language` (string) — optional, defaults to `en`.
  - Parakeet: only `en` is accepted; other values return HTTP 400
  - Whisper: model-dependent; typically multilingual
- `batch` (boolean) — optional, defaults to `false`.

Notes:

- Provide either `file` or `files`, not both. If neither is provided, HTTP 400.
- `batch` requires `files`; using `batch=true` without `files` returns HTTP 400.
- Response shape for multiple files is the same regardless of `batch`.
- Files sent to this endpoint are processed in a single pass (no VAD/chunking). This is intended for short clips (roughly ≤ 30s; depends on GPU memory/model). For longer audio, prefer `/v1/audio/transcriptions-from-url` which supports VAD-based chunking.

Responses

Single file response:

```json
{
  "text": "transcribed text",
  "words": [
    { "word": "hello", "start": 0.0, "end": 0.5 },
    { "word": "world", "start": 0.5, "end": 1.0 }
  ],
  "filename": "audio.mp3"
}
```

Multiple files response:

```json
{
  "results": [
    {"filename": "a1.mp3", "text": "...", "words": [...]},
    {"filename": "a2.mp3", "text": "...", "words": [...]}]
}
```

Notes:

- Word objects always include keys: `word`, `start`, `end`.
- Some implementations may include a trailing space in `word` to match Whisper tokenization behavior; clients should trim if needed.

Example curl (single file):

```bash
curl -X POST \
  -H "Authorization: Bearer $REFLECTOR_GPU_APIKEY" \
  -F "file=@/path/to/audio.mp3" \
  -F "language=en" \
  "$BASE_URL/v1/audio/transcriptions"
```

Example curl (multiple files, batch):

```bash
curl -X POST \
  -H "Authorization: Bearer $REFLECTOR_GPU_APIKEY" \
  -F "files=@/path/a1.mp3" -F "files=@/path/a2.mp3" \
  -F "batch=true" -F "language=en" \
  "$BASE_URL/v1/audio/transcriptions"
```

#### POST /v1/audio/transcriptions-from-url

Transcribe a single remote audio file by URL.

Request: application/json

Body parameters:

- `audio_file_url` (string) — required. URL of the audio file to transcribe.
- `model` (string) — optional. Defaults to the implementation-specific model (see above).
- `language` (string) — optional, defaults to `en`. Parakeet only accepts `en`.
- `timestamp_offset` (number) — optional, defaults to `0.0`. Added to each word's `start`/`end` in the response.

```json
{
  "audio_file_url": "https://example.com/audio.mp3",
  "model": "nvidia/parakeet-tdt-0.6b-v2",
  "language": "en",
  "timestamp_offset": 0.0
}
```

Response:

```json
{
  "text": "transcribed text",
  "words": [
    { "word": "hello", "start": 10.0, "end": 10.5 },
    { "word": "world", "start": 10.5, "end": 11.0 }
  ]
}
```

Notes:

- `timestamp_offset` is added to each word’s `start`/`end` in the response.
- Implementations may perform VAD-based chunking and batching for long-form audio; word timings are adjusted accordingly.

Example curl:

```bash
curl -X POST \
  -H "Authorization: Bearer $REFLECTOR_GPU_APIKEY" \
  -H "Content-Type: application/json" \
  -d '{
        "audio_file_url": "https://example.com/audio.mp3",
        "language": "en",
        "timestamp_offset": 0
      }' \
  "$BASE_URL/v1/audio/transcriptions-from-url"
```

### Error handling

- 400 Bad Request
  - Parakeet: `language` other than `en`
  - Missing required parameters (`file`/`files` for upload; `audio_file_url` for URL endpoint)
  - Unsupported file extension
- 401 Unauthorized
  - Missing or invalid Bearer token
- 404 Not Found
  - `audio_file_url` does not exist

### Implementation details

- GPUs: A10G for small-file/live, L40S for large-file URL transcription (subject to deployment)
- VAD chunking and segment batching; word timings adjusted and overlapping ends constrained
- Pads very short segments (< 0.5s) to avoid model crashes on some backends

### Server configuration (Reflector API)

Set the Reflector server to use the Modal backend and point `TRANSCRIPT_URL` to your chosen deployment:

```
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://<account>--reflector-transcriber-parakeet-web.modal.run
TRANSCRIPT_MODAL_API_KEY=<REFLECTOR_GPU_APIKEY>
```

### Conformance tests

Use the pytest-based conformance tests to validate any new implementation (including self-hosted) against this spec:

```
TRANSCRIPT_URL=https://<your-deployment-base> \
TRANSCRIPT_MODAL_API_KEY=your-api-key \
uv run -m pytest -m model_api --no-cov server/tests/test_model_api_transcript.py
```
