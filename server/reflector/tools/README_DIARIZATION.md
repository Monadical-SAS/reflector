# Audio Processing with Speaker Diarization

This document describes how to use the extended Reflector CLI tool that supports speaker diarization for local audio files.

## Overview

The `process_with_diarization.py` script extends the basic Reflector CLI to include speaker diarization capabilities. It can process audio files locally without requiring the full Reflector server infrastructure.

## Features

- Process audio files (mp3, wav, mp4, etc.) locally
- Generate transcripts with word-level timestamps
- Detect topics and generate summaries
- **Speaker diarization**: Identify different speakers in the audio
- Support for multiple languages
- Output results in JSONL format

## Installation

### Prerequisites

1. Install the base Reflector dependencies
2. Install additional dependencies for diarization:

```bash
pip install pyannote.audio torch torchaudio
```

### HuggingFace Authentication

Some diarization models (like pyannote) require HuggingFace authentication:

1. Create a HuggingFace account at https://huggingface.co
2. Generate an access token
3. Set the environment variable:

```bash
export HF_TOKEN="your_huggingface_token"
# or
export HUGGINGFACE_TOKEN="your_huggingface_token"
```

## Usage

### Basic Usage (without diarization)

```bash
python reflector/tools/process_with_diarization.py audio.mp3 -o output.jsonl
```

### With Speaker Diarization

```bash
python reflector/tools/process_with_diarization.py audio.mp3 -d -o output.jsonl
```

### Command Line Options

- `source`: Input audio file path (required)
- `--only-transcript`, `-t`: Only generate transcript without topics/summaries
- `--source-language`: Source language code (default: en)
- `--target-language`: Target language code for translation (default: en)
- `--output`, `-o`: Output file path for JSONL results
- `--enable-diarization`, `-d`: Enable speaker diarization
- `--diarization-backend`: Backend to use for diarization (default: local, options: local, modal)

### Examples

1. Process English audio with diarization:
```bash
python reflector/tools/process_with_diarization.py meeting.mp3 -d -o meeting_transcript.jsonl
```

2. Process Spanish audio and translate to English with diarization:
```bash
python reflector/tools/process_with_diarization.py spanish_audio.wav \
    --source-language es \
    --target-language en \
    -d \
    -o spanish_to_english.jsonl
```

3. Quick transcript only (no topics or diarization):
```bash
python reflector/tools/process_with_diarization.py audio.mp3 -t -o transcript.jsonl
```

## Output Format

The tool outputs events in JSONL format. When diarization is enabled, each word in the transcript will include a `speaker` field indicating which speaker said that word.

Example output structure:
```json
{
  "processor": "TranscriptLinerProcessor",
  "data": {
    "transcript": {
      "words": [
        {
          "text": "Hello",
          "start": 0.5,
          "end": 0.8,
          "speaker": 0
        },
        {
          "text": "world",
          "start": 0.9,
          "end": 1.2,
          "speaker": 0
        }
      ]
    }
  }
}
```

## Diarization Backends

### Local Backend

The local backend uses pyannote-audio to perform diarization on your machine. It:
- Downloads the model on first use
- Supports GPU acceleration if available
- Works with local files without uploading to external services
- Requires HuggingFace authentication for some models

### Modal Backend

The modal backend uses the Reflector Modal deployment for diarization. It requires:
- Modal API credentials
- Network connectivity
- Audio files to be uploaded to the service

## Troubleshooting

1. **Authentication Error**: Make sure HF_TOKEN is set for pyannote models
2. **Memory Issues**: Large audio files may require significant RAM
3. **CUDA Errors**: If GPU issues occur, the tool will fall back to CPU
4. **Missing Dependencies**: Install all required packages including pyannote.audio

## Technical Details

The diarization process:
1. Audio is processed through the standard Reflector pipeline
2. Audio is saved to a temporary WAV file during processing
3. Topics are collected during transcription
4. After transcription, diarization runs on the audio file
5. Speaker labels are assigned to each word based on timing
6. Results are emitted with speaker information included