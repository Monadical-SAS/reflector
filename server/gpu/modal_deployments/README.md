# Reflector GPU implementation - Transcription and LLM

This repository hold an API for the GPU implementation of the Reflector API service,
and use [Modal.com](https://modal.com)

- `reflector_diarizer.py` - Diarization API
- `reflector_transcriber.py` - Transcription API
- `reflector_translator.py` - Translation API

## Modal.com deployment

Create a modal secret, and name it `reflector-gpu`.
It should contain an `REFLECTOR_APIKEY` environment variable with a value.

The deployment is done using [Modal.com](https://modal.com) service.

```
$ modal deploy reflector_transcriber.py
...
└── 🔨 Created web => https://xxxx--reflector-transcriber-web.modal.run

$ modal deploy reflector_llm.py
...
└── 🔨 Created web => https://xxxx--reflector-llm-web.modal.run
```

Then in your reflector api configuration `.env`, you can set theses keys:

```
TRANSCRIPT_BACKEND=modal
TRANSCRIPT_URL=https://xxxx--reflector-transcriber-web.modal.run
TRANSCRIPT_MODAL_API_KEY=REFLECTOR_APIKEY

LLM_BACKEND=modal
LLM_URL=https://xxxx--reflector-llm-web.modal.run
LLM_MODAL_API_KEY=REFLECTOR_APIKEY
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
