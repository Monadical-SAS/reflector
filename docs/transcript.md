# Transcript Formats

The Reflector API provides multiple output formats for transcript data through the `transcript_format` query parameter on the GET `/v1/transcripts/{id}` endpoint.

## Overview

When retrieving a transcript, you can specify the desired format using the `transcript_format` query parameter. The API supports four formats optimized for different use cases:

- **text** - Plain text with speaker names (default)
- **text-timestamped** - Timestamped text with speaker names
- **webvtt-named** - WebVTT subtitle format with participant names
- **json** - Structured JSON segments with full metadata

All formats include participant information when available, resolving speaker IDs to actual names.

## Query Parameter Usage

```
GET /v1/transcripts/{id}?transcript_format={format}
```

### Parameters

- `transcript_format` (optional): The desired output format
  - Type: `"text" | "text-timestamped" | "webvtt-named" | "json"`
  - Default: `"text"`

## Format Descriptions

### Text Format (`text`)

**Use case:** Simple, human-readable transcript for display or export.

**Format:** Speaker names followed by their dialogue, one line per segment.

**Example:**
```
John Smith: Hello everyone
Jane Doe: Hi there
John Smith: How are you today?
```

**Request:**
```bash
GET /v1/transcripts/{id}?transcript_format=text
```

**Response:**
```json
{
  "id": "transcript_123",
  "name": "Meeting Recording",
  "transcript_format": "text",
  "transcript": "John Smith: Hello everyone\nJane Doe: Hi there\nJohn Smith: How are you today?",
  "participants": [
    {"id": "p1", "speaker": 0, "name": "John Smith"},
    {"id": "p2", "speaker": 1, "name": "Jane Doe"}
  ],
  ...
}
```

### Text Timestamped Format (`text-timestamped`)

**Use case:** Transcript with timing information for navigation or reference.

**Format:** `[MM:SS]` timestamp prefix before each speaker and dialogue.

**Example:**
```
[00:00] John Smith: Hello everyone
[00:05] Jane Doe: Hi there
[00:12] John Smith: How are you today?
```

**Request:**
```bash
GET /v1/transcripts/{id}?transcript_format=text-timestamped
```

**Response:**
```json
{
  "id": "transcript_123",
  "name": "Meeting Recording",
  "transcript_format": "text-timestamped",
  "transcript": "[00:00] John Smith: Hello everyone\n[00:05] Jane Doe: Hi there\n[00:12] John Smith: How are you today?",
  "participants": [
    {"id": "p1", "speaker": 0, "name": "John Smith"},
    {"id": "p2", "speaker": 1, "name": "Jane Doe"}
  ],
  ...
}
```

### WebVTT Named Format (`webvtt-named`)

**Use case:** Subtitle files for video players, accessibility tools, or video editing.

**Format:** Standard WebVTT subtitle format with voice tags using participant names.

**Example:**
```
WEBVTT

00:00:00.000 --> 00:00:05.000
<v John Smith>Hello everyone

00:00:05.000 --> 00:00:12.000
<v Jane Doe>Hi there

00:00:12.000 --> 00:00:18.000
<v John Smith>How are you today?
```

**Request:**
```bash
GET /v1/transcripts/{id}?transcript_format=webvtt-named
```

**Response:**
```json
{
  "id": "transcript_123",
  "name": "Meeting Recording",
  "transcript_format": "webvtt-named",
  "transcript": "WEBVTT\n\n00:00:00.000 --> 00:00:05.000\n<v John Smith>Hello everyone\n\n...",
  "participants": [
    {"id": "p1", "speaker": 0, "name": "John Smith"},
    {"id": "p2", "speaker": 1, "name": "Jane Doe"}
  ],
  ...
}
```

### JSON Format (`json`)

**Use case:** Programmatic access with full timing and speaker metadata.

**Format:** Array of segment objects with speaker information, text content, and precise timing.

**Example:**
```json
[
  {
    "speaker": 0,
    "speaker_name": "John Smith",
    "text": "Hello everyone",
    "start": 0.0,
    "end": 5.0
  },
  {
    "speaker": 1,
    "speaker_name": "Jane Doe",
    "text": "Hi there",
    "start": 5.0,
    "end": 12.0
  },
  {
    "speaker": 0,
    "speaker_name": "John Smith",
    "text": "How are you today?",
    "start": 12.0,
    "end": 18.0
  }
]
```

**Request:**
```bash
GET /v1/transcripts/{id}?transcript_format=json
```

**Response:**
```json
{
  "id": "transcript_123",
  "name": "Meeting Recording",
  "transcript_format": "json",
  "transcript": [
    {
      "speaker": 0,
      "speaker_name": "John Smith",
      "text": "Hello everyone",
      "start": 0.0,
      "end": 5.0
    },
    {
      "speaker": 1,
      "speaker_name": "Jane Doe",
      "text": "Hi there",
      "start": 5.0,
      "end": 12.0
    }
  ],
  "participants": [
    {"id": "p1", "speaker": 0, "name": "John Smith"},
    {"id": "p2", "speaker": 1, "name": "Jane Doe"}
  ],
  ...
}
```

## Response Structure

All formats return the same base transcript metadata with an additional `transcript_format` field and format-specific `transcript` field:

### Common Fields

- `id`: Transcript identifier
- `user_id`: Owner user ID (if authenticated)
- `name`: Transcript name
- `status`: Processing status
- `locked`: Whether transcript is locked for editing
- `duration`: Total duration in seconds
- `title`: Auto-generated or custom title
- `short_summary`: Brief summary
- `long_summary`: Detailed summary
- `created_at`: Creation timestamp
- `share_mode`: Access control setting
- `source_language`: Original audio language
- `target_language`: Translation target language
- `reviewed`: Whether transcript has been reviewed
- `meeting_id`: Associated meeting ID (if applicable)
- `source_kind`: Source type (live, file, room)
- `room_id`: Associated room ID (if applicable)
- `audio_deleted`: Whether audio has been deleted
- `participants`: Array of participant objects with speaker mappings

### Format-Specific Fields

- `transcript_format`: The format identifier (discriminator field)
- `transcript`: The formatted transcript content (string for text/webvtt formats, array for json format)

## Speaker Name Resolution

All formats resolve speaker IDs to participant names when available:

- If a participant exists for the speaker ID, their name is used
- If no participant exists, a default name like "Speaker 0" is generated
- Speaker IDs are integers (0, 1, 2, etc.) assigned during diarization
