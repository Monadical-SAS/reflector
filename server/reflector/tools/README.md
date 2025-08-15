# Reflector CLI Tools

This directory contains command-line tools for processing audio files with transcription, diarization, and other features without requiring the full server infrastructure.

## Available Tools

### 1. Process with Diarization (`process_with_diarization.py`)

Process audio files with speaker diarization to identify different speakers in the conversation.

#### Basic Usage

```bash
cd /Users/firfi/work/clients/monadical/reflector/server

# With speaker diarization
REDIS_HOST=localhost CELERY_BROKER_URL=redis://localhost:6379/1 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
uv run python -m reflector.tools.process_with_diarization \
  path/to/audio.mp4 \
  --enable-diarization \
  --diarization-backend modal \
  --output output.jsonl
```

#### Prerequisites

1. **Redis must be running:**
   ```bash
   docker compose up -d redis
   ```

2. **Environment variables:**
   - `REDIS_HOST=localhost` - Redis server host
   - `CELERY_BROKER_URL=redis://localhost:6379/1` - Celery broker URL
   - `CELERY_RESULT_BACKEND=redis://localhost:6379/1` - Celery result backend
   - `TRANSCRIPT_MODAL_API_KEY` - Modal API key for transcription (if using Modal backend)
   - `DIARIZATION_MODAL_API_KEY` - Modal API key for diarization (if using Modal backend)

#### Command-line Options

- `source` - Path to the audio/video file (mp3, wav, mp4, etc.)
- `--enable-diarization, -d` - Enable speaker diarization
- `--diarization-backend` - Backend for diarization (default: modal, choices: modal)
- `--only-transcript, -t` - Only generate transcript without topics/summaries
- `--source-language` - Source language code (default: en)
- `--target-language` - Target language code (default: en)
- `--output, -o` - Output file path (JSONL format)

#### Output Format

The tool outputs JSONL (JSON Lines) format with events from the processing pipeline. Key events include:

- **AudioTranscriptModalProcessor** - Raw transcription with word timings
- **TranscriptLinerProcessor** - Transcript organized into lines
- **TranscriptTopicDetectorProcessor** - Detected topics in the conversation
- **AudioDiarizationModalProcessor** - Diarized transcript with speaker IDs
- **TranscriptFinalTitleProcessor** - Generated titles for topics
- **TranscriptFinalSummaryProcessor** - Generated summaries for topics

Example diarization output structure:
```json
{
  "processor": "AudioDiarizationModalProcessor",
  "data": {
    "title": "Topic Title",
    "summary": "Topic summary",
    "timestamp": 0.006,
    "duration": 49.047,
    "transcript": {
      "words": [
        {
          "text": "Hello",
          "start": 0.006,
          "end": 0.246,
          "speaker": 0
        },
        {
          "text": "world",
          "start": 0.250,
          "end": 0.500,
          "speaker": 1
        }
      ]
    }
  }
}
```

#### Example Commands

**Process MP4 file with diarization:**
```bash
REDIS_HOST=localhost CELERY_BROKER_URL=redis://localhost:6379/1 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
uv run python -m reflector.tools.process_with_diarization \
  /path/to/meeting.mp4 \
  --enable-diarization \
  --diarization-backend modal \
  --output meeting_diarized.jsonl
```

**Process audio with translation:**
```bash
REDIS_HOST=localhost CELERY_BROKER_URL=redis://localhost:6379/1 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
uv run python -m reflector.tools.process_with_diarization \
  /path/to/audio.wav \
  --source-language es \
  --target-language en \
  --output translated.jsonl
```

**Transcript only (no topics/summaries):**
```bash
REDIS_HOST=localhost CELERY_BROKER_URL=redis://localhost:6379/1 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
uv run python -m reflector.tools.process_with_diarization \
  /path/to/audio.mp3 \
  --only-transcript \
  --output transcript.jsonl
```

### 2. Process Audio (`process.py`)

Basic audio processing tool for transcription without diarization.

#### Usage

```bash
cd /Users/firfi/work/clients/monadical/reflector/server

REDIS_HOST=localhost \
uv run python -m reflector.tools.process \
  path/to/audio.mp3 \
  --output output.jsonl
```

#### Command-line Options

- `source` - Path to the audio/video file
- `--only-transcript, -t` - Only generate transcript without topics/summaries
- `--source-language` - Source language code (default: en)
- `--target-language` - Target language code (default: en)
- `--output, -o` - Output file path (JSONL format)

### 3. Test Diarization (`test_diarization.py`)

Test script for validating diarization functionality.

#### Usage

```bash
cd /Users/firfi/work/clients/monadical/reflector/server

# Works with any audio/video format (mp4, wav, mp3, etc.)
uv run python reflector/tools/test_diarization.py path/to/test_audio.mp4
```


## Troubleshooting

### Redis Connection Error
```
gaierror: [Errno 8] nodename nor servname provided, or not known
```
**Solution:** Ensure Redis is running and environment variables are set correctly:
```bash
docker compose up -d redis
export REDIS_HOST=localhost
```

### Modal API Error
```
Failed to import diarization dependencies
```
**Solution:** Ensure Modal API keys are set:
```bash
export TRANSCRIPT_MODAL_API_KEY=your_key_here
export DIARIZATION_MODAL_API_KEY=your_key_here
```

## Notes

- Audio files are temporarily stored during processing and cleaned up automatically
- For Modal backend, files are uploaded to S3 for processing
