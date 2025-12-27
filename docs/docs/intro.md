---
sidebar_position: 1
title: Introduction
---

# Welcome to Reflector

Reflector is a privacy-focused, self-hosted AI-powered audio transcription and meeting analysis platform that provides real-time transcription, speaker diarization, translation, and summarization for audio content and live meetings. With complete control over your data and infrastructure, you can run models on your own hardware (roadmap - currently supports Modal.com for GPU processing).

## What is Reflector?

Reflector is a web application that utilizes AI to process audio content, providing:

- **Real-time Transcription**: Convert speech to text using [Whisper](https://github.com/openai/whisper) (multi-language) or [Parakeet](https://github.com/NVIDIA/NeMo) (English) models
- **Speaker Diarization**: Identify and label different speakers using [Pyannote](https://github.com/pyannote/pyannote-audio) 3.1
- **Live Translation**: Translate audio content in real-time to 100+ languages with [Facebook Seamless-M4T](https://github.com/facebookresearch/seamless_communication)
- **Topic Detection & Summarization**: Extract key topics and generate concise summaries using LLMs
- **Meeting Recording**: Create permanent records of meetings with searchable transcripts

## Features

| Feature | Public Mode | Private Mode |
|---------|------------|--------------|
| **Authentication** | None required | Required |
| **Audio Upload** | ✅ | ✅ |
| **Live Microphone Streaming** | ✅ | ✅ |
| **Transcription** | ✅ | ✅ |
| **Speaker Diarization** | ✅ | ✅ |
| **Translation** | ✅ | ✅ |
| **Topic Detection** | ✅ | ✅ |
| **Summarization** | ✅ | ✅ |
| **Virtual Meeting Rooms (Whereby)** | ❌ | ✅ |
| **Browse Transcripts Page** | ❌ | ✅ |
| **Search Functionality** | ❌ | ✅ |
| **Persistent Storage** | ❌ | ✅ |

## Architecture Overview

Reflector consists of three main components:

- **Frontend**: React application built with Next.js 14
- **Backend**: Python server using FastAPI
- **Processing**: Scalable GPU workers for ML inference (Modal.com or local)

## Getting Started

Ready to deploy Reflector? Head over to our [Installation Guide](./installation/overview) to set up your own instance.

For a quick overview of how Reflector processes audio, check out our [Pipeline Documentation](./pipelines/overview).

## Open Source

Reflector is open source software developed by [Monadical](https://monadical.com) and licensed under the **MIT License**. We welcome contributions from the community!

- [GitHub Repository](https://github.com/monadical-sas/reflector)
- [Issue Tracker](https://github.com/monadical-sas/reflector/issues)
- [Pull Requests](https://github.com/monadical-sas/reflector/pulls)

## Support

Need help? Reach out to the community through GitHub Discussions.