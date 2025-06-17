# Audio Storage Consent Flow Requirements

## Current Problem
- Users must consent to recording **before** joining room
- Consent blocks room entry at `/app/[roomName]/page.tsx:80-124`
- Users cannot participate without prior consent

## System Reality: Recording Detection Constraints
- **No real-time recording detection**: System only discovers recordings after they complete (60+ second SQS delay)
- **Cannot stop recordings**: Whereby controls recording entirely based on room configuration
- **Limited webhook events**: Only `room.client.joined/left` available, no recording webhooks
- **Post-processing only**: Can only mark recordings for deletion during transcript processing

## Required Changes

### 1. Remove Pre-Entry Consent Blocking
- **Remove** consent dialog from room entry page
- Allow immediate room joining without consent check

### 2. Request Audio Storage Consent During Meeting Session
- Ask during meeting: **"Do you consent to storing this audio recording?"**
- **Timing**: ALWAYS ask - no conditions, no participant count checks, no configuration checks
- **Scope**: Per meeting session (`meeting_id`), not per room (rooms are reused)
- **Storage**: Dictionary of participants with their consent responses {user_id: true/false} in meeting record

### 3. Handle Consent Responses
- **If ANY participant denies consent:** Mark recording for deletion during post-processing
- **If ALL participants consent:** Keep audio file as normal
- **Always:** Continue meeting, recording, and transcription (cannot be interrupted)

### 4. Audio Deletion Logic
- **Always**: Create transcript, topics, summaries, waveforms first
- **Then**: If consent denied, delete only audio files (`upload.mp4`, `audio.mp3`, `audio.wav`)
- **Keep**: All transcript data, topics, summaries, waveforms (audio content is transcribed)
- **Scope**: Only affects specific meeting's audio files, not other sessions in same room

## Recording Trigger Context
Whereby recording starts based on room configuration:
- `"automatic-2nd-participant"` (default): Recording starts when 2nd person joins
- `"automatic"`: Recording starts immediately when meeting begins
- `"prompt"`: Manual recording start (host control)
- `"none"`: No recording

## Success Criteria
- Users join rooms without barriers
- Audio storage consent requested during meeting (estimated timing)
- Post-processing checks consent and deletes audio if denied
- Transcription and analysis unaffected by consent choice
- Multiple meeting sessions in same room handled independently