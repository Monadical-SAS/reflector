## Reflector GPU Transcription API (Parakeet)

This document describes the GPU transcription API deployed on Modal.com using NVIDIA Parakeet. The API surface and response shapes are OpenAI/Whisper-compatible. If desired, you can switch to a Whisper deployment by changing the base URL; no client changes are required.

### Base URL and Authentication

- Parakeet base URL (Modal web endpoint), for example:

  - `https://<account>--reflector-transcriber-parakeet-web.modal.run`

- All endpoints are served under `/v1` and require a Bearer token:

```
Authorization: Bearer <REFLECTOR_GPU_APIKEY>
```

Note: To use Whisper instead, deploy the Whisper variant and point `TRANSCRIPT_URL` to its base URL (e.g., `https://<account>--reflector-transcriber-web.modal.run`). The API is identical.

### Supported file types

`mp3, mp4, mpeg, mpga, m4a, wav, webm`

### Models and languages

- Parakeet (NVIDIA NeMo): default `nvidia/parakeet-tdt-0.6b-v2`
  - Language: only `en` is supported. Other languages return HTTP 400.

Note: The `model` parameter is accepted for interface parity, but is currently informational for Parakeet.

### Endpoints

#### POST /v1/audio/transcriptions

Transcribe one or more uploaded audio files.

Request: multipart/form-data

- `file`: single file to transcribe
- `files`: multiple files to transcribe
- `model`: optional, defaults to implementation-specific model (see above)
- `language`: language code; Parakeet requires `en`
- `batch`: boolean; when `true` and multiple files are provided, returns a `results` array

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

Multiple files, non-batch mode (processed one-by-one):

```json
{
  "results": [
    {"filename": "a1.mp3", "text": "...", "words": [...]},
    {"filename": "a2.mp3", "text": "...", "words": [...]}]
}
```

Multiple files with `batch=true`:

```json
{
  "results": [
    {"filename": "a1.mp3", "text": "...", "words": [...]},
    {"filename": "a2.mp3", "text": "...", "words": [...]}]
}
```

Notes:

- Word objects always include keys: `word`, `start`, `end`.
- Parakeet may include a trailing space in `word` to match Whisper tokenization behavior; clients should trim if needed.

Example curl (single file):

```bash
curl -X POST \
  -H "Authorization: Bearer $REFLECTOR_GPU_APIKEY" \
  -F "file=@/path/to/audio.mp3" \
  -F "model=nvidia/parakeet-tdt-0.6b-v2" \
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
- Parakeet performs VAD-based chunking for long-form audio.

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
  - `language` other than `en`
  - Missing required parameters (`file`/`files` for upload; `audio_file_url` for URL endpoint)
  - Unsupported file extension
- 401 Unauthorized
  - Missing or invalid Bearer token
- 404 Not Found
  - `audio_file_url` does not exist

### Implementation details

- GPUs: A10G for small-file/live, L40S for large-file URL transcription
- VAD chunking and segment batching; word timings adjusted and overlapping ends constrained
- Pads very short segments (< 0.5s) to avoid model crashes

### Server configuration (Reflector API)

Set the Reflector server to use the Modal backend and point `TRANSCRIPT_URL` to your Parakeet deployment:

```
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://<account>--reflector-transcriber-parakeet-web.modal.run
TRANSCRIPT_MODAL_API_KEY=<REFLECTOR_GPU_APIKEY>
```

To switch to Whisper, simply update `TRANSCRIPT_URL` to the Whisper deployment (e.g., `https://<account>--reflector-transcriber-web.modal.run`). The server integrates via an OpenAI-compatible client, expecting `text` and `words[{word,start,end}]` and supporting both single and multi-file responses per the shapes above.
