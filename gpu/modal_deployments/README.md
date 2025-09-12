# Reflector GPU implementation - Transcription and LLM

This repository hold an API for the GPU implementation of the Reflector API service,
and use [Modal.com](https://modal.com)

- `reflector_diarizer.py` - Diarization API
- `reflector_transcriber.py` - Transcription API (Whisper)
- `reflector_transcriber_parakeet.py` - Transcription API (NVIDIA Parakeet)
- `reflector_translator.py` - Translation API

## Modal.com deployment

Create a modal secret, and name it `reflector-gpu`.
It should contain an `REFLECTOR_APIKEY` environment variable with a value.

The deployment is done using [Modal.com](https://modal.com) service.

```
$ modal deploy reflector_transcriber.py
...
└── 🔨 Created web => https://xxxx--reflector-transcriber-web.modal.run

$ modal deploy reflector_transcriber_parakeet.py
...
└── 🔨 Created web => https://xxxx--reflector-transcriber-parakeet-web.modal.run

$ modal deploy reflector_llm.py
...
└── 🔨 Created web => https://xxxx--reflector-llm-web.modal.run
```

Then in your reflector api configuration `.env`, you can set these keys:

```
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://xxxx--reflector-transcriber-web.modal.run
TRANSCRIPT_MODAL_API_KEY=REFLECTOR_APIKEY

DIARIZATION_BACKEND=modal
DIARIZATION_URL=https://xxxx--reflector-diarizer-web.modal.run
DIARIZATION_MODAL_API_KEY=REFLECTOR_APIKEY

TRANSLATION_BACKEND=modal
TRANSLATION_URL=https://xxxx--reflector-translator-web.modal.run
TRANSLATION_MODAL_API_KEY=REFLECTOR_APIKEY
```

## API

Authentication must be passed with the `Authorization` header, using the `bearer` scheme.

```
Authorization: bearer <REFLECTOR_APIKEY>
```

### LLM

`POST /llm`

**request**
```
{
    "prompt": "xxx"
}
```

**response**
```
{
    "text": "xxx completed"
}
```

### Transcription

#### Parakeet Transcriber (`reflector_transcriber_parakeet.py`)

NVIDIA Parakeet is a state-of-the-art ASR model optimized for real-time transcription with superior word-level timestamps.

**GPU Configuration:**
- **A10G GPU** - Used for `/v1/audio/transcriptions` endpoint (small files, live transcription)
  - Higher concurrency (max_inputs=10)
  - Optimized for multiple small audio files
  - Supports batch processing for efficiency

- **L40S GPU** - Used for `/v1/audio/transcriptions-from-url` endpoint (large files)
  - Lower concurrency but more powerful processing
  - Optimized for single large audio files
  - VAD-based chunking for long-form audio

##### `/v1/audio/transcriptions` - Small file transcription

**request** (multipart/form-data)
- `file` or `files[]` - audio file(s) to transcribe
- `model` - model name (default: `nvidia/parakeet-tdt-0.6b-v2`)
- `language` - language code (default: `en`)
- `batch` - whether to use batch processing for multiple files (default: `true`)

**response**
```json
{
    "text": "transcribed text",
    "words": [
        {"word": "hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 0.5, "end": 1.0}
    ],
    "filename": "audio.mp3"
}
```

For multiple files with batch=true:
```json
{
    "results": [
        {
            "filename": "audio1.mp3",
            "text": "transcribed text",
            "words": [...]
        },
        {
            "filename": "audio2.mp3",
            "text": "transcribed text",
            "words": [...]
        }
    ]
}
```

##### `/v1/audio/transcriptions-from-url` - Large file transcription

**request** (application/json)
```json
{
    "audio_file_url": "https://example.com/audio.mp3",
    "model": "nvidia/parakeet-tdt-0.6b-v2",
    "language": "en",
    "timestamp_offset": 0.0
}
```

**response**
```json
{
    "text": "transcribed text from large file",
    "words": [
        {"word": "hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 0.5, "end": 1.0}
    ]
}
```

**Supported file types:** mp3, mp4, mpeg, mpga, m4a, wav, webm

#### Whisper Transcriber (`reflector_transcriber.py`)

`POST /transcribe`

**request** (multipart/form-data)

- `file` - audio file
- `language` - language code (e.g. `en`)

**response**
```
{
    "text": "xxx",
    "words": [
        {"text": "xxx", "start": 0.0, "end": 1.0}
    ]
}
```
