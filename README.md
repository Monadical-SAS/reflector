<div align="center">

# Reflector

Reflector Audio Management and Analysis is a cutting-edge web application under development by Monadical. It utilizes AI to record meetings, providing a permanent record with transcripts, translations, and automated summaries.

[![Tests](https://github.com/monadical-sas/cubbi/actions/workflows/pytests.yml/badge.svg?branch=main&event=push)](https://github.com/monadical-sas/cubbi/actions/workflows/pytests.yml)
[![License: MIT](https://img.shields.io/badge/license-AGPL--v3-green.svg)](https://opensource.org/licenses/AGPL-v3)
</div>

## Screenshots
<table>
  <tr>
    <td>
      <a href="https://github.com/user-attachments/assets/3a976930-56c1-47ef-8c76-55d3864309e3">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/3a976930-56c1-47ef-8c76-55d3864309e3" />
      </a>
    </td>
    <td>
      <a href="https://github.com/user-attachments/assets/bfe3bde3-08af-4426-a9a1-11ad5cd63b33">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/bfe3bde3-08af-4426-a9a1-11ad5cd63b33" />
      </a>
    </td>
    <td>
      <a href="https://github.com/user-attachments/assets/7b60c9d0-efe4-474f-a27b-ea13bd0fabdc">
        <img width="700" alt="image" src="https://github.com/user-attachments/assets/7b60c9d0-efe4-474f-a27b-ea13bd0fabdc" />
      </a>
    </td>
  </tr>
</table>

## Background

The project architecture consists of three primary components:

- **Front-End**: NextJS React project hosted on Vercel, located in `www/`.
- **Back-End**: Python server that offers an API and data persistence, found in `server/`.
- **GPU implementation**: Providing services such as speech-to-text transcription, topic generation, automated summaries, and translations. Most reliable option is Modal deployment

It also uses authentik for authentication if activated, and Vercel for deployment and configuration of the front-end.

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

### Frontend

Start with `cd backend`.

**Installation**

```bash
yarn install
cp .env_template .env
cp config-template.ts config.ts
```

Then, fill in the environment variables in `.env` and the configuration in `config.ts` as needed. If you are unsure on how to proceed, ask in Zulip.

**Run in development mode**

```bash
yarn dev
```

Then (after completing server setup and starting it) open [http://localhost:3000](http://localhost:3000) to view it in the browser.

**OpenAPI Code Generation**

To generate the TypeScript files from the openapi.json file, make sure the python server is running, then run:

```bash
yarn openapi
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
