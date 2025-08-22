<div align="center">
<img width="100" alt="image" src="https://github.com/user-attachments/assets/66fb367b-2c89-4516-9912-f47ac59c6a7f"/>

# Reflector

Reflector is an AI-powered audio transcription and meeting analysis platform that provides real-time transcription, speaker diarization, translation and summarization for audio content and live meetings. It works 100% with local models (whisper/parakeet, pyannote, seamless-m4t, and your local llm like phi-4).

[![Tests](https://github.com/monadical-sas/reflector/actions/workflows/test_server.yml/badge.svg?branch=main&event=push)](https://github.com/monadical-sas/reflector/actions/workflows/test_server.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](https://opensource.org/licenses/MIT)
</div>
</div>
<table>
  <tr>
    <td>
      <a href="https://github.com/user-attachments/assets/21f5597c-2930-4899-a154-f7bd61a59e97">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/21f5597c-2930-4899-a154-f7bd61a59e97" />
      </a>
    </td>
    <td>
      <a href="https://github.com/user-attachments/assets/f6b9399a-5e51-4bae-b807-59128d0a940c">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/f6b9399a-5e51-4bae-b807-59128d0a940c" />
      </a>
    </td>
    <td>
      <a href="https://github.com/user-attachments/assets/a42ce460-c1fd-4489-a995-270516193897">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/a42ce460-c1fd-4489-a995-270516193897" />
      </a>
    </td>
    <td>
      <a href="https://github.com/user-attachments/assets/21929f6d-c309-42fe-9c11-f1299e50fbd4">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/21929f6d-c309-42fe-9c11-f1299e50fbd4" />
      </a>
    </td>
  </tr>
</table>

## What is Reflector?

Reflector is a web application that utilizes AI to process audio content, providing:

- **Real-time Transcription**: Convert speech to text using [Whisper](https://github.com/openai/whisper) (multi-language) or [Parakeet](https://huggingface.co/nvidia/parakeet-tdt-0.6b-v2) (English) models
- **Speaker Diarization**: Identify and label different speakers using [Pyannote](https://github.com/pyannote/pyannote-audio) 3.1
- **Live Translation**: Translate audio content in real-time to many languages with [Facebook Seamless-M4T](https://github.com/facebookresearch/seamless_communication)
- **Topic Detection & Summarization**: Extract key topics and generate concise summaries using LLMs
- **Meeting Recording**: Create permanent records of meetings with searchable transcripts

Currently we provide [modal.com](https://modal.com/) gpu template to deploy.

## Background

The project architecture consists of three primary components:

- **Back-End**: Python server that offers an API and data persistence, found in `server/`.
- **Front-End**: NextJS React project hosted on Vercel, located in `www/`.
- **GPU implementation**: Providing services such as speech-to-text transcription, topic generation, automated summaries, and translations.

It also uses authentik for authentication if activated.

## Contribution Guidelines

All new contributions should be made in a separate branch, and goes through a Pull Request.
[Conventional commits](https://www.conventionalcommits.org/en/v1.0.0/) must be used for the PR title and commits.

## Usage

To record both your voice and the meeting you're taking part in, you need:

- For an in-person meeting, make sure your microphone is in range of all participants.
- If using several microphones, make sure to merge the audio feeds into one with an external tool.
- For an online meeting, if you do not use headphones, your microphone should be able to pick up both your voice and the audio feed of the meeting.
- If you want to use headphones, you need to merge the audio feeds with an external tool.

Permissions:

You may have to add permission for browser's microphone access to record audio in
`System Preferences -> Privacy & Security -> Microphone`
`System Preferences -> Privacy & Security -> Accessibility`. You will be prompted to provide these when you try to connect.

### How to Install Blackhole (Mac Only)

This is an external tool for merging the audio feeds as explained in the previous section of this document.
Note: We currently do not have instructions for Windows users.

- Install [Blackhole](https://github.com/ExistentialAudio/BlackHole)-2ch (2 ch is enough) by 1 of 2 options listed.
- Setup ["Aggregate device"](https://github.com/ExistentialAudio/BlackHole/wiki/Aggregate-Device) to route web audio and local microphone input.
- Setup [Multi-Output device](https://github.com/ExistentialAudio/BlackHole/wiki/Multi-Output-Device)
- Then goto `System Preferences -> Sound` and choose the devices created from the Output and Input tabs.
- The input from your local microphone, the browser run meeting should be aggregated into one virtual stream to listen to and the output should be fed back to your specified output devices if everything is configured properly.

## Installation

*Note: we're working toward better installation, theses instructions are not accurate for now*

### Frontend

Start with `cd www`.

**Installation**

```bash
pnpm install
cp .env_template .env
cp config-template.ts config.ts
```

Then, fill in the environment variables in `.env` and the configuration in `config.ts` as needed. If you are unsure on how to proceed, ask in Zulip.

**Run in development mode**

```bash
pnpm dev
```

Then (after completing server setup and starting it) open [http://localhost:3000](http://localhost:3000) to view it in the browser.

**OpenAPI Code Generation**

To generate the TypeScript files from the openapi.json file, make sure the python server is running, then run:

```bash
pnpm openapi
```

### Backend

Start with `cd server`.

**Run in development mode**

```bash
docker compose up -d redis

# on the first run, or if the schemas changed
uv run alembic upgrade head

# start the worker
uv run celery -A reflector.worker.app worker --loglevel=info

# start the app
uv run -m reflector.app --reload
```

Then fill `.env` with the omitted values (ask in Zulip).

**Crontab (optional)**

For crontab (only healthcheck for now), start the celery beat (you don't need it on your local dev environment):

```bash
uv run celery -A reflector.worker.app beat
```

### GPU models

Currently, reflector heavily use custom local models, deployed on modal. All the micro services are available in server/gpu/

To deploy llm changes to modal, you need:
- a modal account
- set up the required secret in your modal account (REFLECTOR_GPU_APIKEY)
- install the modal cli
- connect your modal cli to your account if not done previously
- `modal run path/to/required/llm`

## Using local files

You can manually process an audio file by calling the process tool:

```bash
uv run python -m reflector.tools.process path/to/audio.wav
```
