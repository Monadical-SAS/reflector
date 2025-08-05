# Whereby to Daily.co Migration Feasibility Analysis

## Executive Summary

After analysis of the current Whereby integration and Daily.co's capabilities, migrating to Daily.co is technically feasible. The migration can be done in phases:

1. **Phase 1**: Feature parity with current implementation (standard cloud recording)
2. **Phase 2**: Enhanced capabilities with raw-tracks recording for improved diarization

### Current Implementation Analysis

Based on code review:
- **Webhook handling**: The current webhook handler (`server/reflector/views/whereby.py`) only tracks `num_clients`, not individual participants
- **Focus management**: The frontend has 70+ lines managing focus between Whereby embed and consent dialog
- **Participant tracking**: No participant names or IDs are captured in the current implementation
- **Recording type**: Cloud recording to S3 in MP4 format with mixed audio

### Migration Approach

**Phase 1**: 1:1 feature replacement maintaining current functionality:
- Standard cloud recording (same as current Whereby implementation)
- Same recording workflow: Video platform → S3 → Reflector processing
- No changes to existing diarization or transcription pipeline

**Phase 2**: Enhanced capabilities (future implementation):
- Raw-tracks recording for speaker-separated audio
- Improved diarization with participant-to-audio mapping
- Per-participant transcription accuracy

## Current Whereby Integration Analysis

### Backend Integration

#### Core API Module (`server/reflector/whereby.py`)
- **Meeting Creation**: Creates rooms with S3 recording configuration
- **Session Monitoring**: Tracks meeting status via room sessions API
- **Logo Upload**: Handles branding for meetings
- **Key Functions**:
  ```python
  create_meeting(room_name, logo_s3_url) -> dict
  monitor_room_session(meeting_link) -> dict
  upload_logo(file_stream, content_type) -> str
  ```

#### Webhook Handler (`server/reflector/views/whereby.py`)
- **Endpoint**: `/v1/whereby_webhook`
- **Security**: HMAC signature validation
- **Events Handled**:
  - `room.participant.joined`
  - `room.participant.left`
- **Pain Point**: Delay between actual join/leave and webhook delivery

#### Room Management (`server/reflector/views/rooms.py`)
- Creates meetings via Whereby API
- Stores meeting data in database
- Manages recording lifecycle

### Frontend Integration

#### Main Room Component (`www/app/[roomName]/page.tsx`)
- Uses `@whereby.com/browser-sdk` (v3.3.4)
- Implements custom `<whereby-embed>` element
- Handles recording consent
- Focus management for accessibility

#### Configuration
- Environment Variables:
  - `WHEREBY_API_URL`, `WHEREBY_API_KEY`, `WHEREBY_WEBHOOK_SECRET`
  - AWS S3 credentials for recordings
- Recording workflow: Whereby → S3 → Reflector processing pipeline

## Daily.co Capabilities Analysis

### REST API Features

#### Room Management
```
POST /rooms - Create room with configuration
GET /rooms/:name/presence - Real-time participant data
POST /rooms/:name/recordings/start - Start recording
```

#### Recording Options
```json
{
  "enable_recording": "raw-tracks"  // Key feature for diarization
}
```

#### Webhook Events
- `participant.joined` / `participant.left`
- `waiting-participant.joined` / `waiting-participant.left`
- `recording.started` / `recording.ready-to-download`
- `recording.error`

### React SDK (@daily-co/daily-react)

#### Modern Hook-based Architecture
```jsx
// Participant tracking
const participantIds = useParticipantIds({ filter: 'remote' });
const [username, videoState] = useParticipantProperty(id, ['user_name', 'tracks.video.state']);

// Recording management
const { isRecording, startRecording, stopRecording } = useRecording();

// Real-time participant data
const participants = useParticipants();
```

## Feature Comparison

| Feature | Whereby | Daily.co |
|---------|---------|----------|
| **Room Creation** | REST API | REST API |
| **Recording Types** | Cloud (MP4) | Cloud (MP4), Local, Raw-tracks |
| **S3 Integration** | Direct upload | Direct upload with IAM roles |
| **Frontend Integration** | Custom element | React hooks or iframe |
| **Webhooks** | HMAC verified | HMAC verified |
| **Participant Data** | Via webhooks | Via webhooks + Presence API |
| **Recording Trigger** | Automatic/manual | Automatic/manual |

## Migration Plan

### Phase 1: Backend API Client

#### 1.1 Create Daily.co API Client (`server/reflector/daily.py`)

```python
from datetime import datetime
import httpx
from reflector.db.rooms import Room
from reflector.settings import settings

class DailyClient:
    def __init__(self):
        self.base_url = "https://api.daily.co/v1"
        self.headers = {
            "Authorization": f"Bearer {settings.DAILY_API_KEY}",
            "Content-Type": "application/json"
        }
        self.timeout = 10

    async def create_meeting(self, room_name_prefix: str, end_date: datetime, room: Room) -> dict:
        """Create a Daily.co room matching current Whereby functionality."""
        data = {
            "name": f"{room_name_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}",
            "privacy": "private" if room.is_locked else "public",
            "properties": {
                "enable_recording": "raw-tracks", #"cloud",
                "enable_chat": True,
                "enable_screenshare": True,
                "start_video_off": False,
                "start_audio_off": False,
                "exp": int(end_date.timestamp()),
                "enable_recording_ui": False,  # We handle consent ourselves
            }
        }

        # if room.recording_type == "cloud":
        data["properties"]["recording_bucket"] = {
            "bucket_name": settings.AWS_S3_BUCKET,
            "bucket_region": settings.AWS_REGION,
            "assume_role_arn": settings.AWS_DAILY_ROLE_ARN,
            "path": f"recordings/{data['name']}"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/rooms",
                headers=self.headers,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            room_data = response.json()

            # Return in Whereby-compatible format
            return {
                "roomUrl": room_data["url"],
                "hostRoomUrl": room_data["url"] + "?t=" + room_data["config"]["token"],
                "roomName": room_data["name"],
                "meetingId": room_data["id"]
            }

    async def get_room_sessions(self, room_name: str) -> dict:
        """Get room session data (similar to Whereby's insights)."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/rooms/{room_name}",
                headers=self.headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
```

#### 1.2 Update Webhook Handler (`server/reflector/views/daily.py`)

```python
import hmac
import json
from datetime import datetime
from hashlib import sha256
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from reflector.db.meetings import meetings_controller
from reflector.settings import settings

router = APIRouter()

class DailyWebhookEvent(BaseModel):
    type: str
    id: str
    ts: int
    data: dict

def verify_daily_webhook(body: bytes, signature: str) -> bool:
    """Verify Daily.co webhook signature."""
    expected = hmac.new(
        settings.DAILY_WEBHOOK_SECRET.encode(),
        body,
        sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/daily")
async def daily_webhook(event: DailyWebhookEvent, request: Request):
    # Verify webhook signature
    body = await request.body()
    signature = request.headers.get("X-Daily-Signature", "")

    if not verify_daily_webhook(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Handle participant events
    if event.type == "participant.joined":
        meeting = await meetings_controller.get_by_room_name(event.data["room_name"])
        if meeting:
            # Update participant info immediately
            await meetings_controller.add_participant(
                meeting.id,
                participant_id=event.data["participant"]["user_id"],
                name=event.data["participant"]["user_name"],
                joined_at=datetime.fromtimestamp(event.ts / 1000)
            )

    elif event.type == "participant.left":
        meeting = await meetings_controller.get_by_room_name(event.data["room_name"])
        if meeting:
            await meetings_controller.remove_participant(
                meeting.id,
                participant_id=event.data["participant"]["user_id"],
                left_at=datetime.fromtimestamp(event.ts / 1000)
            )

    elif event.type == "recording.ready-to-download":
        # Process cloud recording (same as Whereby)
        meeting = await meetings_controller.get_by_room_name(event.data["room_name"])
        if meeting:
            # Queue standard processing task
            from reflector.worker.tasks import process_recording
            process_recording.delay(
                meeting_id=meeting.id,
                recording_url=event.data["download_link"],
                recording_id=event.data["recording_id"]
            )

    return {"status": "ok"}
```

### Phase 2: Frontend Components

#### 2.1 Replace Whereby SDK with Daily React

First, update dependencies:
```bash
# Remove Whereby
yarn remove @whereby.com/browser-sdk

# Add Daily.co
yarn add @daily-co/daily-react @daily-co/daily-js
```

#### 2.2 New Room Component (`www/app/[roomName]/page.tsx`)

```tsx
"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  DailyProvider,
  useDaily,
  useParticipantIds,
  useRecording,
  useDailyEvent,
  useLocalParticipant,
} from "@daily-co/daily-react";
import { Box, Button, Text, VStack, HStack, Spinner } from "@chakra-ui/react";
import { toaster } from "../components/ui/toaster";
import useRoomMeeting from "./useRoomMeeting";
import { useRouter } from "next/navigation";
import { notFound } from "next/navigation";
import useSessionStatus from "../lib/useSessionStatus";
import { useRecordingConsent } from "../recordingConsentContext";
import DailyIframe from "@daily-co/daily-js";

// Daily.co Call Interface Component
function CallInterface() {
  const daily = useDaily();
  const { isRecording, startRecording, stopRecording } = useRecording();
  const localParticipant = useLocalParticipant();
  const participantIds = useParticipantIds({ filter: "remote" });

  // Real-time participant tracking
  useDailyEvent("participant-joined", useCallback((event) => {
    console.log(`${event.participant.user_name} joined the call`);
    // No need for webhooks - we have immediate access!
  }, []));

  useDailyEvent("participant-left", useCallback((event) => {
    console.log(`${event.participant.user_name} left the call`);
  }, []));

  return (
    <Box position="relative" width="100vw" height="100vh">
      {/* Daily.co automatically handles the video/audio UI */}
      <Box
        as="iframe"
        src={daily?.iframe()?.src}
        width="100%"
        height="100%"
        allow="camera; microphone; fullscreen; speaker; display-capture"
        style={{ border: "none" }}
      />

      {/* Recording status indicator */}
      {isRecording && (
        <Box
          position="absolute"
          top={4}
          right={4}
          bg="red.500"
          color="white"
          px={3}
          py={1}
          borderRadius="md"
          fontSize="sm"
        >
          Recording
        </Box>
      )}

      {/* Participant count with real-time data */}
      <Box position="absolute" bottom={4} left={4} bg="gray.800" color="white" px={3} py={1} borderRadius="md">
        Participants: {participantIds.length + 1}
      </Box>
    </Box>
  );
}

// Main Room Component with Daily.co Integration
export default function Room({ params }: { params: { roomName: string } }) {
  const roomName = params.roomName;
  const meeting = useRoomMeeting(roomName);
  const router = useRouter();
  const { isLoading, isAuthenticated } = useSessionStatus();
  const [dailyUrl, setDailyUrl] = useState<string | null>(null);
  const [callFrame, setCallFrame] = useState<DailyIframe | null>(null);

  // Initialize Daily.co call
  useEffect(() => {
    if (!meeting?.response?.room_url) return;

    const frame = DailyIframe.createCallObject({
      showLeaveButton: true,
      showFullscreenButton: true,
    });

    frame.on("left-meeting", () => {
      router.push("/browse");
    });

    setCallFrame(frame);
    setDailyUrl(meeting.response.room_url);

    return () => {
      frame.destroy();
    };
  }, [meeting?.response?.room_url, router]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" height="100vh">
        <Spinner color="blue.500" size="xl" />
      </Box>
    );
  }

  if (!dailyUrl || !callFrame) {
    return null;
  }

  return (
    <DailyProvider callObject={callFrame} url={dailyUrl}>
      <CallInterface />
      <ConsentDialog meetingId={meeting?.response?.id} />
    </DailyProvider>
  );
}

### Phase 3: Testing & Validation

For Phase 1 (feature parity), the existing processing pipeline remains unchanged:

1. Daily.co records meeting to S3 (same as Whereby)
2. Webhook notifies when recording is ready
3. Existing pipeline downloads and processes the MP4 file
4. Current diarization and transcription tools continue to work

Key validation points:
- Recording format matches (MP4 with mixed audio)
- S3 paths are compatible
- Processing pipeline requires no changes
- Transcript quality remains the same

## Future Enhancement: Raw-Tracks Recording (Phase 2)

### Raw-Tracks Processing for Enhanced Diarization

Daily.co's raw-tracks recording provides individual audio streams per participant, enabling:

```python
@shared_task
def process_daily_raw_tracks(meeting_id: str, recording_id: str, tracks: list):
    """Process Daily.co raw-tracks with perfect speaker attribution."""

    for track in tracks:
        participant_id = track["participant_id"]
        participant_name = track["participant_name"]
        track_url = track["download_url"]

        # Download individual participant audio
        response = download_track(track_url)

        # Process with known speaker identity
        transcript = transcribe_audio(
            audio_data=response.content,
            speaker_id=participant_id,
            speaker_name=participant_name
        )

        # Store with accurate speaker mapping
        save_transcript_segment(
            meeting_id=meeting_id,
            speaker_id=participant_id,
            text=transcript.text,
            timestamps=transcript.timestamps
        )
```

### Benefits of Raw-Tracks (Future)

1. **Deterministic Speaker Attribution**: Each audio track is already speaker-separated
2. **Improved Transcription Accuracy**: Clean audio without cross-talk
3. **Parallel Processing**: Process multiple speakers simultaneously
4. **Better Metrics**: Accurate talk-time per participant

### Phase 4: Database & Configuration

#### 4.1 Environment Variable Updates

Update `.env` files:

```bash
# Remove Whereby variables
# WHEREBY_API_URL=https://api.whereby.dev/v1
# WHEREBY_API_KEY=your-whereby-key
# WHEREBY_WEBHOOK_SECRET=your-whereby-secret
# AWS_WHEREBY_S3_BUCKET=whereby-recordings
# AWS_WHEREBY_ACCESS_KEY_ID=whereby-key
# AWS_WHEREBY_ACCESS_KEY_SECRET=whereby-secret

# Add Daily.co variables
DAILY_API_KEY=your-daily-api-key
DAILY_WEBHOOK_SECRET=your-daily-webhook-secret
AWS_DAILY_S3_BUCKET=daily-recordings
AWS_DAILY_ROLE_ARN=arn:aws:iam::123456789:role/daily-recording-role
AWS_REGION=us-west-2
```

#### 4.2 Database Migration

```sql
-- Alembic migration to support Daily.co
-- server/alembic/versions/xxx_migrate_to_daily.py

def upgrade():
    # Add platform field to support gradual migration
    op.add_column('rooms', sa.Column('platform', sa.String(), server_default='whereby'))
    op.add_column('meetings', sa.Column('platform', sa.String(), server_default='whereby'))

    # No other schema changes needed for feature parity

def downgrade():
    op.drop_column('meetings', 'platform')
    op.drop_column('rooms', 'platform')
```

#### 4.3 Settings Update (`server/reflector/settings.py`)

```python
class Settings(BaseSettings):
    # Remove Whereby settings
    # WHEREBY_API_URL: str = "https://api.whereby.dev/v1"
    # WHEREBY_API_KEY: str
    # WHEREBY_WEBHOOK_SECRET: str
    # AWS_WHEREBY_S3_BUCKET: str
    # AWS_WHEREBY_ACCESS_KEY_ID: str
    # AWS_WHEREBY_ACCESS_KEY_SECRET: str

    # Add Daily.co settings
    DAILY_API_KEY: str
    DAILY_WEBHOOK_SECRET: str
    AWS_DAILY_S3_BUCKET: str
    AWS_DAILY_ROLE_ARN: str
    AWS_REGION: str = "us-west-2"

    # Daily.co room URL pattern
    DAILY_ROOM_URL_PATTERN: str = "https://{subdomain}.daily.co/{room_name}"
    DAILY_SUBDOMAIN: str = "reflector"  # Your Daily.co subdomain
```

## Technical Differences

### Phase 1 Implementation
1. **Frontend**: Replace `<whereby-embed>` custom element with Daily.co React components or iframe
2. **Backend**: Create Daily.co API client matching Whereby's functionality
3. **Webhooks**: Map Daily.co events to existing database operations
4. **Recording**: Maintain same MP4 format and S3 storage

### Phase 2 Capabilities (Future)
1. **Raw-tracks recording**: Individual audio streams per participant
2. **Presence API**: Real-time participant data without webhook delays
3. **Transcription API**: Built-in transcription services
4. **Advanced recording options**: Multiple formats and layouts

## Risks and Mitigation

### Risk 1: API Differences
- **Mitigation**: Create abstraction layer to minimize changes
- Comprehensive testing of all endpoints

### Risk 2: Recording Format Changes
- **Mitigation**: Build adapter for raw-tracks processing
- Maintain backward compatibility during transition

### Risk 3: User Experience Changes
- **Mitigation**: A/B testing with gradual rollout
- Feature parity checklist before full migration

## Recommendation

Migration to Daily.co is technically feasible and can be implemented in phases:

### Phase 1: Feature Parity
- Replace Whereby with Daily.co maintaining exact same functionality
- Use standard cloud recording (MP4 to S3)
- No changes to processing pipeline

### Phase 2: Enhanced Capabilities (Future)
- Enable raw-tracks recording for improved diarization
- Implement participant-level audio processing
- Add real-time features using Presence API

## Next Steps

1. Set up Daily.co account and obtain API credentials
2. Implement feature flag system for gradual migration
3. Create Daily.co API client matching Whereby functionality
4. Update frontend to support both platforms
5. Test thoroughly before rollout

---

*Analysis based on current codebase review and API documentation comparison.*
