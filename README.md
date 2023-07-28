# Reflector

Reflector server is responsible for audio transcription and summarization for now.
_The project is moving fast, documentation is currently unstable and outdated_

## Server

We currently use oogabooga as a LLM backend.

### Using docker

Create a `.env` with

```
LLM_URL=http://IP:HOST/api/v1/generate
```

Then start with:

```
$ docker-compose up
```

