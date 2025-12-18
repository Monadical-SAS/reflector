---
title: API Reference
---

# API Reference

The Reflector API provides a comprehensive RESTful interface for audio transcription, meeting management, and real-time streaming capabilities.

## Base URL

```
http://localhost:8000/v1
```

All API endpoints are prefixed with `/v1/` for versioning.

## Authentication

Reflector supports multiple authentication modes:

- **No Authentication** (Public Mode): Basic transcription and upload functionality
- **JWT Authentication** (Private Mode): Full feature access including meeting rooms and persistent storage
- **OAuth/OIDC via Authentik**: Enterprise single sign-on integration

## Core Endpoints

### Transcripts

Manage audio transcriptions and their associated metadata.

#### List Transcripts
```http
GET /v1/transcripts/
```

Returns a paginated list of transcripts with filtering options.

#### Create Transcript
```http
POST /v1/transcripts/
```

Create a new transcript from uploaded audio or initialize for streaming.

#### Get Transcript
```http
GET /v1/transcripts/{transcript_id}
```

Retrieve detailed information about a specific transcript.

#### Update Transcript
```http
PATCH /v1/transcripts/{transcript_id}
```

Update transcript metadata, summary, or processing status.

#### Delete Transcript
```http
DELETE /v1/transcripts/{transcript_id}
```

Remove a transcript and its associated data.

### Audio Processing

#### Upload Audio
```http
POST /v1/transcripts_audio/{transcript_id}/upload
```

Upload an audio file for transcription processing.

**Supported formats:**
- WAV, MP3, M4A, FLAC, OGG
- Maximum file size: 500MB
- Sample rates: 8kHz - 48kHz

#### Download Audio
```http
GET /v1/transcripts_audio/{transcript_id}/download
```

Download the original or processed audio file.

#### Stream Audio
```http
GET /v1/transcripts_audio/{transcript_id}/stream
```

Stream audio content with range support for progressive playback.

### WebRTC Streaming

Real-time audio streaming via WebRTC for live transcription.

#### Initialize WebRTC Session
```http
POST /v1/transcripts_webrtc/{transcript_id}/offer
```

Create a WebRTC offer for establishing a peer connection.

#### Complete WebRTC Handshake
```http
POST /v1/transcripts_webrtc/{transcript_id}/answer
```

Submit the WebRTC answer to complete connection setup.

### WebSocket Streaming

Real-time updates and live transcription via WebSocket.

#### WebSocket Endpoint
```ws
ws://localhost:8000/v1/transcripts_websocket/{transcript_id}
```

Receive real-time transcription updates, speaker changes, and processing status.

**Message Types:**
- `transcription`: New transcribed text segments
- `diarization`: Speaker identification updates
- `status`: Processing status changes
- `error`: Error notifications

### Meetings

Manage virtual meeting rooms and recordings.

#### List Meetings
```http
GET /v1/meetings/
```

Get all meetings for the authenticated user.

#### Create Meeting
```http
POST /v1/meetings/
```

Initialize a new meeting room with Whereby integration.

#### Join Meeting
```http
POST /v1/meetings/{meeting_id}/join
```

Join an existing meeting and start recording.

#### End Meeting
```http
POST /v1/meetings/{meeting_id}/end
```

End the meeting and finalize the recording.

### Rooms

Virtual meeting room configuration and management.

#### List Rooms
```http
GET /v1/rooms/
```

Get available meeting rooms.

#### Create Room
```http
POST /v1/rooms/
```

Create a new persistent meeting room.

#### Update Room Settings
```http
PATCH /v1/rooms/{room_id}
```

Modify room configuration and permissions.

## Response Formats

### Success Response
```json
{
  "id": "uuid",
  "created_at": "2025-01-20T10:00:00Z",
  "updated_at": "2025-01-20T10:30:00Z",
  "data": {...}
}
```

### Error Response
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {...}
  }
}
```

### Status Codes

- `200 OK`: Successful request
- `201 Created`: Resource created successfully
- `204 No Content`: Successful deletion
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Resource conflict
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

## WebSocket Protocol

The WebSocket connection provides real-time updates during transcription processing. The server sends structured messages to communicate different events and data updates.

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/v1/transcripts_websocket/{transcript_id}');
```

### Message Types and Formats

#### Transcription Update
Sent when new text is transcribed from the audio stream.
```json
{
  "type": "transcription",
  "data": {
    "text": "The transcribed text segment",
    "speaker": "Speaker 1",
    "timestamp": 1705745623.456,
    "confidence": 0.95,
    "segment_id": "seg_001",
    "is_final": true
  }
}
```

#### Diarization Update
Sent when speaker changes are detected or speaker labels are updated.
```json
{
  "type": "diarization",
  "data": {
    "speaker": "Speaker 2",
    "speaker_id": "spk_002",
    "start_time": 1705745620.123,
    "end_time": 1705745625.456,
    "confidence": 0.87
  }
}
```

#### Processing Status
Sent to indicate changes in the processing pipeline status.
```json
{
  "type": "status",
  "data": {
    "status": "processing",
    "stage": "transcription",
    "progress": 45.5,
    "message": "Processing audio chunk 12 of 26"
  }
}
```

Status values:
- `initializing`: Setting up processing pipeline
- `processing`: Active transcription/diarization
- `completed`: Processing finished successfully
- `failed`: Processing encountered an error
- `paused`: Processing temporarily suspended

#### Summary Update
Sent when AI-generated summaries or topics are available.
```json
{
  "type": "summary",
  "data": {
    "summary": "Brief summary of the conversation",
    "topics": ["topic1", "topic2", "topic3"],
    "action_items": ["action 1", "action 2"],
    "key_points": ["point 1", "point 2"]
  }
}
```

#### Error Messages
Sent when errors occur during processing.
```json
{
  "type": "error",
  "data": {
    "code": "AUDIO_FORMAT_ERROR",
    "message": "Unsupported audio format",
    "details": {
      "format": "unknown",
      "sample_rate": 0
    },
    "recoverable": false
  }
}
```

#### Heartbeat/Keepalive
Sent periodically to maintain the connection.
```json
{
  "type": "ping",
  "data": {
    "timestamp": 1705745630.000
  }
}
```

### Client-to-Server Messages

Clients can send control messages to the server:

#### Start/Resume Processing
```json
{
  "action": "start",
  "params": {}
}
```

#### Pause Processing
```json
{
  "action": "pause",
  "params": {}
}
```

#### Request Status
```json
{
  "action": "get_status",
  "params": {}
}
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:

```
http://localhost:8000/v1/openapi.json
```

You can import this specification into tools like:
- Postman
- Insomnia
- Swagger UI
- OpenAPI Generator (for client SDK generation)

## SDK Support

While Reflector doesn't provide official SDKs, you can generate client libraries using the OpenAPI specification with tools like:

- **Python**: `openapi-python-client`
- **TypeScript**: `openapi-typescript-codegen`
- **Go**: `oapi-codegen`
- **Java**: `openapi-generator`

## Example Usage

### Python Example
```python
import requests

# Upload and transcribe audio
with open('meeting.mp3', 'rb') as f:
    response = requests.post(
        'http://localhost:8000/v1/transcripts/',
        files={'file': f}
    )
    transcript_id = response.json()['id']

# Check transcription status
status = requests.get(
    f'http://localhost:8000/v1/transcripts/{transcript_id}'
).json()

print(f"Transcription status: {status['status']}")
```

### JavaScript WebSocket Example
```javascript
// Connect to WebSocket for real-time transcription updates
const ws = new WebSocket(`ws://localhost:8000/v1/transcripts_websocket/${transcriptId}`);

ws.onopen = () => {
    console.log('Connected to transcription WebSocket');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch(message.type) {
        case 'transcription':
            console.log(`[${message.data.speaker}]: ${message.data.text}`);
            break;
        case 'diarization':
            console.log(`Speaker change: ${message.data.speaker}`);
            break;
        case 'status':
            console.log(`Status: ${message.data.status}`);
            break;
        case 'error':
            console.error(`Error: ${message.data.message}`);
            break;
    }
};

ws.onerror = (error) => {
    console.error('WebSocket error:', error);
};

ws.onclose = () => {
    console.log('WebSocket connection closed');
};
```

## Need Help?

- Review [example implementations](https://github.com/monadical-sas/reflector/tree/main/examples)
- Open an issue on [GitHub](https://github.com/monadical-sas/reflector/issues)