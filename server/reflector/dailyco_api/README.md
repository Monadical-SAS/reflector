# Daily.co API Models

Pydantic models for Daily.co REST API requests, responses, and webhook events.

## Purpose

This module provides strongly-typed models for all Daily.co API interactions:
- **Request models**: Validate outgoing API requests
- **Response models**: Parse and validate API responses
- **Webhook models**: Validate incoming webhook events

All models include links to official Daily.co documentation.

## API Documentation

**Main References:**
- [Daily.co REST API](https://docs.daily.co/reference/rest-api)
- [Webhook Events](https://docs.daily.co/reference/rest-api/webhooks)
- [Raw Tracks Recordings](https://docs.daily.co/reference/rest-api/recordings/raw-tracks-recordings)

## API Endpoints Coverage

### Rooms

- **POST** `/v1/rooms` - Create room
  - Request: `CreateRoomRequest`
  - Response: `RoomResponse`
  - [Docs](https://docs.daily.co/reference/rest-api/rooms/create-room)

- **GET** `/v1/rooms/{room_name}/presence` - Get room presence
  - Response: `RoomPresenceResponse`
  - [Docs](https://docs.daily.co/reference/rest-api/rooms/get-room-presence)

- **DELETE** `/v1/rooms/{room_name}` - Delete room
  - [Docs](https://docs.daily.co/reference/rest-api/rooms/delete-room)

### Meetings

- **GET** `/v1/meetings/{meeting_id}` - Get meeting information
  - Response: `MeetingResponse`
  - Returns: room, duration, participants, ongoing status
  - [Docs](https://docs.daily.co/reference/rest-api/meetings/get-meeting-information)

- **GET** `/v1/meetings/{meeting_id}/participants` - Get meeting participants (paginated)
  - Response: `MeetingParticipantsResponse`
  - Params: `limit`, `joined_after`, `joined_before`
  - [Docs](https://docs.daily.co/reference/rest-api/meetings/get-meeting-participants)

### Recordings

- **GET** `/v1/recordings/{recording_id}` - Get recording info
  - Response: `RecordingResponse`
  - [Docs](https://docs.daily.co/reference/rest-api/recordings/get-recording-info)

### Meeting Tokens

- **POST** `/v1/meeting-tokens` - Create meeting token
  - Request: `CreateMeetingTokenRequest`
  - Response: `MeetingTokenResponse`
  - [Docs](https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token)

### Webhooks

- **GET** `/v1/webhooks` - List webhooks
  - Response: `WebhookListResponse`
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/list-webhooks)

- **POST** `/v1/webhooks` - Create webhook
  - Request: `CreateWebhookRequest`
  - Response: `WebhookResponse`
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/create-webhook)

- **PATCH** `/v1/webhooks/{uuid}` - Update webhook
  - Request: `UpdateWebhookRequest`
  - Note: May require delete + recreate pattern

- **DELETE** `/v1/webhooks/{uuid}` - Delete webhook
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/delete-webhook)

## Webhook Events

All webhook events follow the `DailyWebhookEvent` structure with event-specific payloads.

### Participant Events

- **`participant.joined`** - Participant joined room
  - Payload: `ParticipantJoinedPayload`
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/participant-events)

- **`participant.left`** - Participant left room
  - Payload: `ParticipantLeftPayload`
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/participant-events)

### Recording Events

- **`recording.started`** - Recording started
  - Payload: `RecordingStartedPayload`
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/recording-events)

- **`recording.ready-to-download`** - Recording complete and uploaded
  - Payload: `RecordingReadyToDownloadPayload`
  - Includes `tracks` array for multitrack recordings
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/recording-events)

- **`recording.error`** - Recording failed
  - Payload: `RecordingErrorPayload`
  - [Docs](https://docs.daily.co/reference/rest-api/webhooks/recording-events)

## Webhook Signature Verification

Daily.co signs webhooks using HMAC-SHA256:

1. Headers:
   - `X-Webhook-Signature`: Base64-encoded signature
   - `X-Webhook-Timestamp`: Timestamp string

2. Signature computation:
   ```python
   import hmac
   import base64
   from hashlib import sha256

   secret_bytes = base64.b64decode(webhook_secret)
   signed_content = timestamp.encode() + b"." + request_body
   expected = base64.b64encode(
       hmac.new(secret_bytes, signed_content, sha256).digest()
   ).decode()
   ```

3. Compare using `hmac.compare_digest()` to prevent timing attacks

**Reference:** [Webhook Security](https://docs.daily.co/reference/rest-api/webhooks/webhook-security)

## Important Notes

### API Inconsistencies

- **Room name field**: Different events use different field names:
  - `room_name` - Used in recording events
  - `room` - Used in participant events
  - Both fields are optional in payload models for compatibility

### Webhook Circuit Breaker

After 3+ consecutive failures (4xx/5xx responses), webhook state changes to `FAILED` and stops sending events.

**Recovery:** Delete and recreate webhook using `scripts/recreate_daily_webhook.py`

### Multitrack Recordings

When `enable_recording: "raw-tracks"` is set:
- Each participant's audio/video is recorded separately
- `recording.ready-to-download` event includes `tracks` array
- Each track has: `type` (audio/video), `s3Key`, `size`
- S3 bucket must be configured with `recordings_bucket` in room properties

## Usage Examples

### Quick Start with DailyApiClient

```python
from reflector.dailyco_api import DailyApiClient, CreateRoomRequest, RoomProperties

# Initialize client
client = DailyApiClient(
    api_key="your_daily_api_key",
    webhook_secret="base64_encoded_secret"  # Optional, for webhook verification
)

# Create a room
room = await client.create_room(
    CreateRoomRequest(
        name="my-meeting-20250113143000",
        privacy="private",
        properties=RoomProperties(
            enable_recording="raw-tracks",
            enable_chat=True,
            exp=1705161600,  # Unix timestamp
        )
    )
)
print(f"Room created: {room.url}")

# Get room presence (who's currently in the room)
presence = await client.get_room_presence("my-meeting-20250113143000")
print(f"Participants in room: {presence.total_count}")
for participant in presence.data:
    print(f"  - {participant.userName} (joined {participant.joinTime})")

# Get full meeting information (after meeting ends)
meeting = await client.get_meeting(room.id)
print(f"Meeting duration: {meeting.duration}s")
print(f"Max participants: {meeting.max_participants}")
print(f"Ongoing: {meeting.ongoing}")

# Get meeting participants (paginated)
participants = await client.get_meeting_participants(room.id, limit=10)
for p in participants.data:
    print(f"{p.user_name} was in meeting for {p.duration}s")

# Pagination example
all_participants = []
last_participant_id = None
while True:
    try:
        page = await client.get_meeting_participants(
            room.id,
            limit=50,
            joined_after=last_participant_id
        )
        all_participants.extend(page.data)
        if page.data:
            last_participant_id = page.data[-1].participant_id
        else:
            break
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            break  # No more participants
        raise

# Create meeting token for participant
from reflector.dailyco_api import CreateMeetingTokenRequest, MeetingTokenProperties

token_response = await client.create_meeting_token(
    CreateMeetingTokenRequest(
        properties=MeetingTokenProperties(
            room_name="my-meeting-20250113143000",
            user_id="user_123",
            start_cloud_recording=False,
        )
    )
)
print(f"Meeting token: {token_response.token}")

# Delete room
deleted = await client.delete_room("my-meeting-20250113143000")
print(f"Room deleted: {deleted}")
```

### Webhook Management

```python
from reflector.dailyco_api import (
    DailyApiClient,
    CreateWebhookRequest,
)

client = DailyApiClient(api_key="your_api_key")

# List all webhooks
webhooks = await client.list_webhooks()
for wh in webhooks:
    print(f"Webhook {wh.uuid}: {wh.url} (state: {wh.state})")

# Create webhook
webhook = await client.create_webhook(
    CreateWebhookRequest(
        url="https://your-server.com/v1/daily/webhook",
        eventTypes=[
            "participant.joined",
            "participant.left",
            "recording.started",
            "recording.ready-to-download",
            "recording.error",
        ],
        hmac="your_base64_encoded_secret",
    )
)
print(f"Created webhook {webhook.uuid}")

# Find webhooks by pattern
ngrok_webhooks = await client.find_webhooks_by_pattern("ngrok")
print(f"Found {len(ngrok_webhooks)} ngrok webhooks")

# Delete webhook
await client.delete_webhook(webhook.uuid)
```

### Webhook Verification and Parsing

```python
from fastapi import Request, HTTPException
from reflector.dailyco_api import (
    DailyWebhookEvent,
    verify_webhook_signature,
    extract_room_name,
    parse_webhook_payload,
)

@router.post("/webhook")
async def handle_daily_webhook(request: Request):
    # Get raw body and headers
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")

    # Verify signature
    if not verify_webhook_signature(body, signature, timestamp, WEBHOOK_SECRET):
        raise HTTPException(status_code=401, detail="Invalid signature")

    # Parse event
    event = DailyWebhookEvent(**json.loads(body))

    # Extract room name (handles API inconsistency)
    room_name = extract_room_name(event)

    # Parse typed payload based on event type
    payload = parse_webhook_payload(event)

    # Handle specific events
    if event.type == "participant.joined":
        from reflector.dailyco_api import ParticipantJoinedPayload
        joined = ParticipantJoinedPayload(**event.payload)
        print(f"User {joined.user_name} joined room {room_name}")

    elif event.type == "recording.ready-to-download":
        from reflector.dailyco_api import parse_recording_ready
        recording = parse_recording_ready(event)

        # Get audio tracks only
        audio_tracks = [t for t in recording.tracks or [] if t.type == "audio"]
        for track in audio_tracks:
            print(f"Audio track ready: s3://{track.s3Key} ({track.size} bytes)")

    return {"status": "ok"}
```

### Manual Webhook Payload Parsing

```python
from reflector.dailyco_api import (
    DailyWebhookEvent,
    parse_participant_joined,
    parse_participant_left,
    parse_recording_ready,
    parse_recording_error,
)

event = DailyWebhookEvent(**webhook_data)

if event.type == "participant.joined":
    payload = parse_participant_joined(event)
    print(f"Participant {payload.user_id} joined at {payload.joined_at}")

elif event.type == "participant.left":
    payload = parse_participant_left(event)
    print(f"Participant was in meeting for {payload.duration}s")

elif event.type == "recording.ready-to-download":
    payload = parse_recording_ready(event)
    print(f"Recording has {len(payload.tracks or [])} tracks")

elif event.type == "recording.error":
    payload = parse_recording_error(event)
    print(f"Recording error: {payload.error}")
```

### Using Pydantic Models Directly

```python
from reflector.dailyco_api import (
    CreateRoomRequest,
    RoomProperties,
    RecordingsBucketConfig,
)

# Build complex room configuration
room_config = CreateRoomRequest(
    name="production-meeting",
    privacy="private",
    properties=RoomProperties(
        enable_recording="raw-tracks",
        enable_chat=True,
        enable_screenshare=True,
        start_video_off=False,
        start_audio_off=False,
        recordings_bucket=RecordingsBucketConfig(
            bucket_name="my-recordings-bucket",
            bucket_region="us-east-1",
            assume_role_arn="arn:aws:iam::123456789:role/DailyRecordings",
            allow_api_access=True,
        ),
    )
)

# Convert to dict for API call (excludes None values)
request_data = room_config.model_dump(exclude_none=True)

# Or use the client directly
room = await client.create_room(room_config)
```

## Migration Plan

This module is currently standalone and does NOT modify existing code. Future migration steps:

1. Update `reflector/video_platforms/daily.py` to use these models
2. Update `reflector/views/daily.py` webhook handlers to use these models
3. Update scripts in `scripts/` to use these models
4. Add integration tests using these models
5. Consider creating a unified `DailyClient` class that uses these models

## Development

When adding new endpoints or webhook events:

1. Add request model to `requests.py`
2. Add response model to `responses.py`
3. Add webhook payload model to `webhooks.py` (if applicable)
4. Update this README with links to Daily.co docs
5. Run type checking: `mypy reflector/dailyco_api/`
