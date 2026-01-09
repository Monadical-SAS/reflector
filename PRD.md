# PRD: Dual Recording Support (Cloud + Raw-Tracks)

## Overview

Enable simultaneous Daily.co cloud recording (Brady Bunch grid MP4) and raw-tracks recording (per-participant WebM audio files) for meetings. Cloud recording provides instant playback with video layout, raw-tracks enable high-quality per-speaker transcription.

## Goals

1. Store both cloud MP4 and raw-tracks WebM files from Daily.co meetings
2. Enable users to play back original cloud recording alongside processed transcription
3. Maintain existing transcription quality (raw-tracks only, no changes)
4. Keep implementation simple - validate approach works, add complexity only if needed

## Non-Goals

- Video player implementation (audio playback only in MVP)
- Cloud recording as transcription fallback (if raw-tracks fails, transcript fails)
- Transcribing cloud MP4 audio
- Room-level toggle (always enable both recordings for all meetings)
- Unit tests (manual validation only)

---

## Technical Background

### Daily.co Recording Configuration

**Room `enable_recording` property:**
- **Purpose:** Allows manual recording start (does NOT auto-start)
- **Values:** Single string - `"cloud"` OR `"raw-tracks"` OR `"local"` (NOT array)
- **Current code:** Set to `"raw-tracks"` when Reflector's `room.recording_type == "cloud"` (line 61-62 of `server/reflector/video_platforms/daily.py`)

**JWT `start_cloud_recording` property:**
- **Purpose:** Auto-starts cloud recording when participant joins
- **Current code:** Set to `true` but **DEAD CODE** - room has `enable_recording: "raw-tracks"` so JWT setting ignored (line 189 in `daily.py`, called at line 589 in `views/rooms.py`)

**Frontend `startRecording()` call:**
- **Current code:** Every participant calls `startRecording({ type: "raw-tracks" })` on join (line 236 of `www/app/[roomName]/components/DailyRoom.tsx`)
- **Behavior:** Multiple participants = multiple calls to Daily.co

**instanceId:**
- **Purpose:** UUID identifying a recording session (per Daily.co docs)
- **Per-user:** Each participant joining generates their own instanceId (ephemeral, not stored)
- **Question:** Can cloud + raw-tracks share same instanceId? Docs unclear - needs validation

### Daily.co Support Guidance

From Discord conversation (Kyle + rajneesh, Sept 2024):

> **Kyle:** "We need both raw-tracks and cloud recording. When we start recording from JS and backend it doesn't work."
>
> **rajneesh (Daily.co support):** "It is possible to get both 'raw-tracks' and 'cloud-recording' at the same time. Start the cloud recording using **daily-js API** and then start raw-tracks using the **REST API endpoint**. Please note you need to pass a unique instanceId in the startRecording call."

**Interpretation:**
- Cloud recording: Start via `frame.startRecording()` (daily-js, frontend)
- Raw-tracks recording: Start via `POST /rooms/:name/recordings/start` (REST API, backend)
- Both need instanceId parameter

---

## Solution Architecture

### Recording Trigger Flow

```
User joins meeting
    ↓
Frontend: Generate instanceId (useState, per component mount)
    ↓
Frontend: Start cloud recording via daily-js
    ↓   (instanceId: <uuid>)
Frontend: Call backend endpoint
    ↓
Backend: Start raw-tracks via Daily.co REST API
    ↓   (instanceId: <uuid> - SAME as cloud)
    ↓
Daily.co: Process recordings (assumption: handles duplicate start calls)
    ↓
Webhook: recording.ready-to-download (type: "cloud")
    ↓
Backend: Store s3_key in meeting table
    ↓
Webhook: recording.ready-to-download (type: "raw-tracks")
    ↓
Backend: Queue multitrack processing (existing pipeline)
```

**Key assumptions:**
1. **Every participant** calls both APIs (no first-participant detection)
2. **Daily.co handles idempotency** - multiple start calls to same room don't create duplicate recordings
3. **Same instanceId works** for both cloud and raw-tracks

**Validation required:** Test that multiple participants starting recordings doesn't cause issues.

---

## Implementation Steps

### Phase 0: Preparation & Validation

#### Step 0.1: Prototype instanceId approach

**Before implementing**, validate Daily.co behavior:

```bash
# Test script: server/scripts/test_daily_dual_recording.py

# Test 1: Same instanceId
# 1. Create Daily room with enable_recording: "raw-tracks"
# 2. POST /rooms/:name/recordings/start { type: "cloud", instance_id: "test-123" }
# 3. POST /rooms/:name/recordings/start { type: "raw-tracks", instance_id: "test-123" }
# Expected: Both succeed, webhooks arrive with same/different instance_id

# Test 2: Multiple start calls (simulate multiple participants)
# 1. POST /rooms/:name/recordings/start { type: "cloud", instance_id: "test-123" }
# 2. POST /rooms/:name/recordings/start { type: "cloud", instance_id: "test-123" }  # duplicate
# Expected: Second call is idempotent (no error, no duplicate recording)

# Test 3: Different instanceIds (fallback if same fails)
# 1. POST /rooms/:name/recordings/start { type: "cloud", instance_id: "cloud-123" }
# 2. POST /rooms/:name/recordings/start { type: "raw-tracks", instance_id: "raw-456" }
# Expected: Both succeed independently
```

**Document findings:**
- Add results to `server/DAILYCO_TEST.md`
- Update PRD if different instanceId approach required

**Acceptance criteria:**
- Know which instanceId strategy works
- Know if Daily.co handles duplicate start calls gracefully

---

#### Step 0.2: Remove dead JWT start_cloud_recording

**File:** `server/reflector/video_platforms/daily.py`

**Current code (lines 177-200):**
```python
async def create_meeting_token(
    self,
    room_name: DailyRoomName,
    start_cloud_recording: bool,  # ← Dead parameter
    enable_recording_ui: bool,
    user_id: NonEmptyString | None = None,
    is_owner: bool = False,
    max_recording_duration_seconds: int | None = None,
) -> NonEmptyString:
    start_cloud_recording_opts = None
    if start_cloud_recording and max_recording_duration_seconds:
        start_cloud_recording_opts = {"maxDuration": max_recording_duration_seconds}

    properties = MeetingTokenProperties(
        room_name=room_name,
        user_id=user_id,
        start_cloud_recording=start_cloud_recording,  # ← Dead code
        start_cloud_recording_opts=start_cloud_recording_opts,  # ← Dead code
        enable_recording_ui=enable_recording_ui,
        is_owner=is_owner,
    )
    request = CreateMeetingTokenRequest(properties=properties)
    result = await self._api_client.create_meeting_token(request)
    return result.token
```

**Changes:**
```python
async def create_meeting_token(
    self,
    room_name: DailyRoomName,
    enable_recording_ui: bool,
    user_id: NonEmptyString | None = None,
    is_owner: bool = False,
) -> NonEmptyString:
    # Removed: start_cloud_recording, max_recording_duration_seconds, start_cloud_recording_opts

    properties = MeetingTokenProperties(
        room_name=room_name,
        user_id=user_id,
        enable_recording_ui=enable_recording_ui,
        is_owner=is_owner,
    )
    request = CreateMeetingTokenRequest(properties=properties)
    result = await self._api_client.create_meeting_token(request)
    return result.token
```

**File:** `server/reflector/views/rooms.py`

**Update call site (around line 587-593):**
```python
# Before
token = await client.create_meeting_token(
    meeting.room_name,
    start_cloud_recording=meeting.recording_type == "cloud",  # ← Remove
    enable_recording_ui=enable_recording_ui,
    user_id=user_id,
    is_owner=user_id == room.user_id,
    max_recording_duration_seconds=remaining_seconds,  # ← Remove
)

# After
token = await client.create_meeting_token(
    meeting.room_name,
    enable_recording_ui=enable_recording_ui,
    user_id=user_id,
    is_owner=user_id == room.user_id,
)
```

**Verification:**
```bash
cd server && uv run mypy reflector/video_platforms/daily.py reflector/views/rooms.py
```

**Expected:** No type errors

---

#### Step 0.3: Update frontend recording start

**File:** `www/app/[roomName]/components/DailyRoom.tsx`

**Current code (lines 231-243):**
```typescript
const handleFrameJoinMeeting = useCallback(
  (startRecording: (args: { type: "raw-tracks" }) => void) => {
    try {
      if (meeting.recording_type === "cloud") {
        console.log("Starting cloud recording");
        startRecording({ type: "raw-tracks" });  // ← Wrong type, every participant calls
      }
    } catch (error) {
      console.error("Failed to start recording:", error);
    }
  },
  [meeting.recording_type],
);
```

**Changes:**
```typescript
const [recordingInstanceId] = useState(() => crypto.randomUUID());

const handleFrameJoinMeeting = useCallback(
  (startRecording: (args: { type: "raw-tracks" | "cloud", instanceId: string }) => void) => {
    try {
      if (meeting.recording_type === "cloud") {
        console.log("Starting dual recording", { instanceId: recordingInstanceId });

        // 1. Start cloud recording via daily-js (frontend)
        startRecording({
          type: "cloud",
          instanceId: recordingInstanceId
        });

        // 2. Start raw-tracks via backend REST API
        fetch(`/v1/meetings/${meeting.id}/recordings/start`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            type: "raw-tracks",
            instanceId: recordingInstanceId  // SAME instanceId
          })
        })
          .then(res => {
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            console.log("Raw-tracks recording started via backend");
          })
          .catch(err => {
            console.error("Failed to start raw-tracks recording:", err);
          });
      }
    } catch (error) {
      console.error("Failed to start recordings:", error);
    }
  },
  [meeting.recording_type, recordingInstanceId, meeting.id],
);
```

**Verification:**
```bash
cd www && pnpm tsc --noEmit
```

**Expected:** No type errors

---

### Phase 1: Database Schema

#### Step 1.1: Add cloud recording fields to Meeting table

**File:** `server/reflector/db/migrations/versions/YYYYMMDD_HHMM_add_cloud_recording.py` (NEW)

**Migration:**
```python
"""add cloud recording support

Revision ID: <generated>
Revises: <previous>
Create Date: 2026-01-09 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '<generated>'
down_revision = '<previous>'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('meeting', sa.Column('cloud_recording_s3_key', sa.String(), nullable=True))
    op.add_column('meeting', sa.Column('cloud_recording_duration', sa.Integer(), nullable=True))


def downgrade():
    op.drop_column('meeting', 'cloud_recording_duration')
    op.drop_column('meeting', 'cloud_recording_s3_key')
```

**Run migration:**
```bash
cd server && uv run alembic revision --autogenerate -m "add cloud recording support"
cd server && uv run alembic upgrade head
```

**Verification:**
```bash
docker compose exec postgres psql -U reflector -d reflector -c "\d meeting" | grep cloud_recording
```

**Expected output:**
```
 cloud_recording_s3_key     | character varying |           |          |
 cloud_recording_duration   | integer           |           |          |
```

---

#### Step 1.2: Update DB models

**File:** `server/reflector/db/meetings.py`

**Changes (around line 94):**
```python
class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    start_date: datetime
    end_date: datetime
    room_id: str | None
    is_locked: bool = False
    room_mode: Literal["normal", "group"] = "normal"
    recording_type: Literal["none", "local", "cloud"] = "cloud"
    recording_trigger: Literal[
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    num_clients: int = 0
    is_active: bool = True
    calendar_event_id: str | None = None
    calendar_metadata: dict[str, Any] | None = None
    platform: Platform = WHEREBY_PLATFORM
    # NEW FIELDS:
    cloud_recording_s3_key: str | None = None
    cloud_recording_duration: int | None = None
```

**Add to table definition (around line 14):**
```python
meetings = sa.Table(
    "meeting",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    # ... existing columns ...
    sa.Column("cloud_recording_s3_key", sa.String, nullable=True),
    sa.Column("cloud_recording_duration", sa.Integer, nullable=True),
    # ... rest of columns ...
)
```

**Verification:**
```bash
cd server && uv run mypy reflector/db/meetings.py
```

**Expected:** No type errors

---

### Phase 2: Daily.co API Client Extension

#### Step 2.1: Add start_recording method

**File:** `server/reflector/dailyco_api/client.py`

**Add method after `list_recordings`:**
```python
async def start_recording(
    self,
    room_name: str,
    recording_type: Literal["cloud", "raw-tracks"],
    instance_id: str,
) -> dict:
    """Start recording via REST API.

    Reference: https://docs.daily.co/reference/rest-api/rooms/recordings/start

    Args:
        room_name: Daily.co room name
        recording_type: "cloud" (Brady Bunch MP4) or "raw-tracks" (per-participant WebM)
        instance_id: UUID for this recording session (same ID can be used for both types)

    Returns:
        Recording start confirmation from Daily.co API
    """
    client = await self._get_client()
    response = await client.post(
        f"/rooms/{room_name}/recordings/start",
        json={
            "type": recording_type,
            "instance_id": instance_id,
        },
    )
    return await self._handle_response(response, "start_recording")
```

**Verification:**
```bash
cd server && uv run mypy reflector/dailyco_api/client.py
```

**Expected:** No type errors

---

#### Step 2.2: Expose method in DailyClient wrapper

**File:** `server/reflector/video_platforms/daily.py`

**Add method after `create_meeting_token`:**
```python
async def start_recording(
    self,
    room_name: str,
    recording_type: Literal["cloud", "raw-tracks"],
    instance_id: str,
) -> dict:
    """Start recording via Daily.co REST API.

    Proxies call to Daily.co REST API endpoint.
    """
    return await self._api_client.start_recording(
        room_name=room_name,
        recording_type=recording_type,
        instance_id=instance_id,
    )
```

**Verification:**
```bash
cd server && uv run mypy reflector/video_platforms/daily.py
```

**Expected:** No type errors

---

### Phase 3: Backend Endpoint for Raw-Tracks Start

#### Step 3.1: Create meetings API endpoint

**File:** `server/reflector/views/meetings.py` (NEW)

```python
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from reflector.db.meetings import meetings_controller
from reflector.storage import get_dailyco_storage
from reflector.video_platforms.factory import create_platform_client

logger = logging.getLogger(__name__)

router = APIRouter()


class StartRecordingRequest(BaseModel):
    type: str  # "raw-tracks" (cloud started from frontend)
    instanceId: str


@router.post("/meetings/{meeting_id}/recordings/start")
async def start_recording(meeting_id: str, body: StartRecordingRequest):
    """Start raw-tracks recording via Daily.co REST API.

    Called by frontend after starting cloud recording via daily-js.
    Uses same instanceId to link both recordings.

    Note: No authentication required - anonymous users supported.
    """
    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if body.type != "raw-tracks":
        raise HTTPException(
            status_code=400,
            detail="Only raw-tracks can be started via this endpoint (cloud uses daily-js)",
        )

    try:
        client = create_platform_client("daily")
        result = await client.start_recording(
            room_name=meeting.room_name,
            recording_type=body.type,
            instance_id=body.instanceId,
        )

        logger.info(
            "Started raw-tracks recording via REST API",
            extra={
                "meeting_id": meeting_id,
                "room_name": meeting.room_name,
                "instance_id": body.instanceId,
            }
        )

        return {"status": "ok", "result": result}

    except Exception as e:
        logger.error(
            "Failed to start raw-tracks recording",
            extra={"meeting_id": meeting_id, "error": str(e)}
        )
        raise HTTPException(status_code=500, detail=f"Failed to start recording: {str(e)}")


@router.get("/meetings/{meeting_id}/cloud-recording")
async def get_cloud_recording(meeting_id: str):
    """Serve cloud recording MP4 file.

    Returns redirect to S3 presigned URL from DAILYCO_STORAGE bucket.
    Daily.co writes MP4 there, we read via presigned URL.

    Note: No authentication required - anonymous users supported.
    """
    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.cloud_recording_s3_key:
        raise HTTPException(status_code=404, detail="Cloud recording not available")

    # Generate presigned URL for Daily.co S3 bucket (where Daily writes MP4)
    storage = get_dailyco_storage()
    presigned_url = await storage.get_file_url(
        meeting.cloud_recording_s3_key,
        expires_in=3600,  # 1 hour
    )

    return RedirectResponse(url=presigned_url)
```

**File:** `server/reflector/app.py`

**Register router:**
```python
from reflector.views.meetings import router as meetings_router

app.include_router(meetings_router, prefix="/v1/meetings", tags=["meetings"])
```

**Verification:**
```bash
cd server && uv run mypy reflector/views/meetings.py reflector/app.py
```

**Expected:** No type errors

---

### Phase 4: Webhook Handler Updates

#### Step 4.1: Update recording.ready-to-download handler

**File:** `server/reflector/views/daily.py`

**Replace `_handle_recording_ready` function (around line 174):**
```python
async def _handle_recording_ready(event: RecordingReadyEvent):
    room_name = event.payload.room_name
    recording_id = event.payload.recording_id
    recording_type = event.payload.type  # "cloud" or "raw-tracks"

    logger.info(
        "Recording ready for download",
        extra={
            "room_name": room_name,
            "recording_id": recording_id,
            "recording_type": recording_type,
            "platform": "daily",
        }
    )

    bucket_name = settings.DAILYCO_STORAGE_AWS_BUCKET_NAME
    if not bucket_name:
        logger.error("DAILYCO_STORAGE_AWS_BUCKET_NAME not configured")
        return

    if recording_type == "cloud":
        # Cloud recording: single MP4 file written by Daily.co to DAILYCO_STORAGE bucket
        s3_key = event.payload.s3_key

        # Store cloud recording reference in meeting table
        meeting = await meetings_controller.get_by_room_name(room_name)
        if not meeting:
            logger.warning(
                "Cloud recording: meeting not found",
                extra={"room_name": room_name, "recording_id": recording_id}
            )
            return

        await meetings_controller.update_meeting(
            meeting.id,
            cloud_recording_s3_key=s3_key,
            cloud_recording_duration=event.payload.duration,
        )

        logger.info(
            "Cloud recording stored",
            extra={
                "meeting_id": meeting.id,
                "s3_key": s3_key,
                "duration": event.payload.duration,
            }
        )

    elif recording_type == "raw-tracks":
        # Existing multi-track processing (unchanged)
        tracks = event.payload.tracks
        if not tracks:
            logger.warning(
                "raw-tracks recording: missing tracks array",
                extra={"room_name": room_name, "recording_id": recording_id}
            )
            return

        track_keys = [t.s3Key for t in tracks if t.type == "audio"]

        logger.info(
            "Raw-tracks recording queuing processing",
            extra={
                "recording_id": recording_id,
                "room_name": room_name,
                "num_tracks": len(track_keys),
            }
        )

        process_multitrack_recording.delay(
            bucket_name=bucket_name,
            daily_room_name=room_name,
            recording_id=recording_id,
            track_keys=track_keys,
        )

    else:
        logger.warning(
            "Unknown recording type",
            extra={"recording_type": recording_type, "recording_id": recording_id}
        )
```

**Verification:**
```bash
cd server && uv run mypy reflector/views/daily.py
```

**Expected:** No type errors

---

### Phase 5: Meeting API Updates

#### Step 5.1: Add cloud recording info to Meeting response

**File:** `server/reflector/views/rooms.py`

**Update Meeting schema (around line 55):**
```python
class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    start_date: datetime
    end_date: datetime
    user_id: str | None = None
    room_id: str | None = None
    is_locked: bool = False
    room_mode: Literal["normal", "group"] = "normal"
    recording_type: Literal["none", "local", "cloud"] = "cloud"
    recording_trigger: Literal[
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    num_clients: int = 0
    is_active: bool = True
    calendar_event_id: str | None = None
    calendar_metadata: dict[str, Any] | None = None
    platform: Platform
    # NEW FIELDS:
    cloud_recording_available: bool = False
    cloud_recording_duration: int | None = None
```

**Update `rooms_join_meeting` handler to include cloud recording info:**
```python
@router.post("/rooms/{room_name}/meeting/{meeting_id}/join", response_model=Meeting)
async def rooms_join_meeting(
    room_name: str,
    meeting_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    # ... existing logic ...

    # Build response with cloud recording info
    meeting_dict = meeting.__dict__.copy()
    meeting_dict["cloud_recording_available"] = bool(meeting.cloud_recording_s3_key)
    meeting_dict["cloud_recording_duration"] = meeting.cloud_recording_duration

    return Meeting(**meeting_dict)
```

**Verification:**
```bash
cd server && uv run mypy reflector/views/rooms.py
```

**Expected:** No type errors

---

### Phase 6: Frontend Display

#### Step 6.1: Update transcript page to show cloud recording

**File:** `www/app/(app)/transcripts/[transcriptId]/page.tsx`

**Add after existing audio player section:**
```typescript
{transcript.meeting?.cloud_recording_available && (
  <Box mt={6} p={4} borderWidth="1px" borderRadius="md" bg="gray.50">
    <Flex alignItems="center" mb={2}>
      <Icon as={VideoIcon} mr={2} />
      <Text fontSize="md" fontWeight="bold">
        Original Cloud Recording
      </Text>
    </Flex>
    <Text fontSize="sm" color="gray.600" mb={3}>
      Brady Bunch grid layout (MP4 with video and mixed audio from Daily.co)
    </Text>
    <audio
      controls
      src={`${process.env.NEXT_PUBLIC_REFLECTOR_API_URL}/v1/meetings/${transcript.meeting_id}/cloud-recording`}
      style={{ width: '100%' }}
    >
      Your browser does not support audio playback.
    </audio>
    {transcript.meeting.cloud_recording_duration && (
      <Text fontSize="xs" color="gray.500" mt={2}>
        Duration: {Math.floor(transcript.meeting.cloud_recording_duration / 60)}m{' '}
        {transcript.meeting.cloud_recording_duration % 60}s
      </Text>
    )}
    <Text fontSize="xs" color="orange.600" mt={1}>
      ⚠️ Large file (~38 MB/minute). May take time to load.
    </Text>
  </Box>
)}
```

**Verification:**
```bash
cd www && pnpm tsc --noEmit
```

**Expected:** No type errors

---

### Phase 7: Manual Testing & Validation

#### Step 7.1: End-to-end validation

**Prerequisites:**
```bash
# Ensure services running
docker compose up -d postgres redis server worker

# Verify env vars
grep -E "DAILY_API_KEY|DAILYCO_STORAGE" server/.env
```

**Test procedure:**

**1. Create room:**
```bash
curl -X POST http://localhost:1250/v1/rooms \
  -H "Content-Type: application/json" \
  -d '{
    "name": "dual-recording-test",
    "platform": "daily",
    "recording_type": "cloud",
    "recording_trigger": "automatic-2nd-participant",
    "zulip_auto_post": false,
    "zulip_stream": "",
    "zulip_topic": "",
    "is_locked": false,
    "room_mode": "normal",
    "is_shared": true,
    "webhook_url": "",
    "webhook_secret": "",
    "skip_consent": false
  }'
```

**2. Create meeting:**
```bash
curl -X POST http://localhost:1250/v1/rooms/dual-recording-test/meeting \
  -H "Content-Type: application/json" \
  -d '{"allow_duplicated": false}'
```

**3. Join meeting (single user):**
- Open `http://localhost:3000/rooms/dual-recording-test`
- Click meeting link
- Allow camera/microphone

**4. Monitor browser console:**
```
Starting dual recording { instanceId: "abc-def-..." }
Raw-tracks recording started via backend
```

**5. Monitor server logs:**
```bash
docker compose logs server --tail 50 --follow | grep recording
```

**Expected:**
```
[info] Started raw-tracks recording via REST API | meeting_id=... | instance_id=abc-def-...
```

**6. Speak for 20-30 seconds, then leave meeting**

**7. Wait 2-5 minutes for Daily.co processing**

**8. Monitor webhooks:**
```bash
docker compose logs server --tail 100 --follow | grep "recording.ready"
```

**Expected (2 separate webhooks):**
```
[info] Recording ready for download | recording_type=cloud
[info] Cloud recording stored | s3_key=monadical/.../....mp4

[info] Recording ready for download | recording_type=raw-tracks
[info] Raw-tracks recording queuing processing | num_tracks=1
```

**9. Verify database:**
```bash
docker compose exec postgres psql -U reflector -d reflector -c "
  SELECT
    m.id,
    m.cloud_recording_s3_key,
    m.cloud_recording_duration,
    t.status,
    t.title
  FROM meeting m
  LEFT JOIN transcript t ON t.meeting_id = m.id
  WHERE m.room_name LIKE 'dual-recording-test-%'
  ORDER BY m.created_at DESC
  LIMIT 1;
"
```

**Expected:**
```
                  id                  |          cloud_recording_s3_key           | cloud_recording_duration | status |        title
--------------------------------------+-------------------------------------------+--------------------------+--------+---------------------
 <uuid>                               | monadical/dual-recording-test-.../....mp4 | 23                       | ended  | Test Recording
```

**10. Test cloud recording endpoint:**
```bash
MEETING_ID="<uuid-from-above>"
curl -I "http://localhost:1250/v1/meetings/$MEETING_ID/cloud-recording"
```

**Expected:**
```
HTTP/1.1 307 Temporary Redirect
location: https://reflector-dailyco-local.s3.amazonaws.com/.../recording.mp4?X-Amz-...
```

**11. Test frontend display:**
- Navigate to `http://localhost:3000/transcripts/<transcript-id>`
- Verify "Original Cloud Recording" section appears
- Click play button
- Verify audio plays

**Expected:** Both audio players functional

---

#### Step 7.2: Test multiple participants (validate Daily.co behavior)

**Test:** Do multiple participants starting recordings cause issues?

**Setup:**
1. Create new meeting (same room or new)
2. Open 2 browser windows (or 1 normal + 1 incognito)

**Procedure:**
1. Join meeting from both windows **nearly simultaneously** (within 1 second)
2. Check browser console in both - both should call startRecording
3. Check server logs - should see 2x backend recording start calls
4. Check Daily.co dashboard - how many recording instances created?

**Expected outcomes:**

**Best case:** Daily.co handles idempotency
- Only 1 cloud recording created
- Only 1 raw-tracks recording created
- Both webhooks arrive once

**Acceptable case:** Duplicate recordings but no errors
- 2 cloud recordings created (can delete extra later)
- 2 raw-tracks recordings created (can delete extra later)
- Processing succeeds

**Bad case:** Errors or corruption
- Daily.co returns error on duplicate start
- Recordings fail
- Transcription broken

**Action based on results:**
- **Best/Acceptable:** Ship as-is, document behavior
- **Bad:** Implement lock mechanism (see Alternative Solutions below)

---

## Alternative Solutions

### If Multiple Participants Cause Issues (Implement ONLY If Needed)

**Symptom:** Daily.co returns error when multiple participants start recordings, OR duplicate recordings cause problems

**Solution A: Database Lock (Simple)**

Add first-participant detection with DB-level locking:

```python
# server/reflector/db/meetings.py - add new field
class Meeting(BaseModel):
    # ... existing fields ...
    recording_started: bool = False  # NEW

# Add column migration
op.add_column('meeting', sa.Column('recording_started', sa.Boolean(), nullable=False, server_default=sa.false()))

# In views/rooms.py - rooms_join_meeting
async def rooms_join_meeting(...):
    # ... existing logic ...

    # Check and set recording_started atomically
    async with get_database().transaction():
        meeting = await meetings_controller.get_by_id(meeting_id)
        is_first_participant = not meeting.recording_started

        if is_first_participant:
            await meetings_controller.update_meeting(
                meeting.id,
                recording_started=True
            )

    meeting_dict["is_first_participant"] = is_first_participant
    return Meeting(**meeting_dict)
```

**Frontend change:**
```typescript
// Only start if is_first_participant
if (joinedMeeting.is_first_participant) {
  startRecording({ type: "cloud", instanceId });
  fetch(`/v1/meetings/${meeting.id}/recordings/start`, ...);
}
```

**Pro:** Simple, uses existing DB infrastructure
**Con:** Extra DB roundtrip on join

---

**Solution B: Redis Lock (Better Performance)**

Use Redis for distributed locking:

```python
# In views/rooms.py
from reflector.redis_cache import RedisAsyncLock

async def rooms_join_meeting(...):
    # ... existing logic ...

    is_first_participant = False
    lock_key = f"meeting:{meeting_id}:recording-start"

    try:
        async with RedisAsyncLock(lock_key, timeout=5, blocking_timeout=0):
            # Check if recording already started
            if not await redis.get(f"meeting:{meeting_id}:recording-started"):
                await redis.set(f"meeting:{meeting_id}:recording-started", "1")
                is_first_participant = True
    except LockError:
        # Another participant is starting recording right now
        is_first_participant = False

    meeting_dict["is_first_participant"] = is_first_participant
    return Meeting(**meeting_dict)
```

**Pro:** Fast, no DB changes needed
**Con:** Depends on Redis being available (already required)

---

### If Same instanceId Causes Conflicts

**Symptom:** Daily.co returns error when starting raw-tracks with same instanceId as cloud

**Solution:** Use different instanceIds for cloud vs raw-tracks

**Frontend changes:**
```typescript
const [cloudInstanceId] = useState(() => crypto.randomUUID());
const [rawInstanceId] = useState(() => crypto.randomUUID());

// Use different IDs
startRecording({ type: "cloud", instanceId: cloudInstanceId });

fetch(`/v1/meetings/${meeting.id}/recordings/start`, {
  body: JSON.stringify({
    type: "raw-tracks",
    instanceId: rawInstanceId  // DIFFERENT
  })
});
```

**Backend:** No changes needed (accepts any instanceId)

**Correlation:** Rely on `type` field in webhook payload only (both have same `room_name`)

**Documentation:** Add note to DAILYCO_TEST.md explaining different instanceId requirement

---

## Success Criteria

### Functional Requirements

- [ ] Both cloud and raw-tracks recordings start when user joins meeting
- [ ] Cloud recording webhook stores S3 key in meeting table (DAILYCO_STORAGE bucket)
- [ ] Raw-tracks webhook triggers existing multitrack pipeline (unchanged)
- [ ] Cloud recording accessible via `/v1/meetings/{id}/cloud-recording` endpoint (presigned URL)
- [ ] Transcript page displays cloud recording audio player when available
- [ ] Existing transcription quality unchanged (raw-tracks only)
- [ ] Dead code removed (JWT start_cloud_recording)

### Validation Requirements

- [ ] Prototype test confirms same instanceId works for both cloud and raw-tracks
- [ ] Multi-participant test confirms Daily.co handles duplicate starts gracefully (or lock implemented)
- [ ] End-to-end test shows both webhooks arriving and data stored correctly
- [ ] Cloud recording playback works in frontend

### Non-Functional Requirements

- [ ] No performance degradation in webhook handling
- [ ] Database migration runs without errors
- [ ] Type checking passes (mypy, tsc)

### Rollback Plan

If issues detected in production:

**Immediate mitigation:**
1. Revert frontend DailyRoom.tsx to remove dual recording start
2. This stops cloud recordings (raw-tracks continue normally)

**Database rollback:**
```bash
docker compose exec server uv run alembic downgrade -1
```

**Code rollback:**
1. Revert frontend changes
2. Revert backend webhook handler to only handle raw-tracks
3. Keep API endpoints (harmless if unused)

---

## Storage Impact Estimation

**Scenario:** 10 meetings/day, 30 minutes average, 2 participants

**Before (raw-tracks only):**
- Raw tracks: 2 participants × 30 min × 0.1 MB/min = 6 MB/meeting
- Processed MP3: ~2 MB/meeting
- Total: 8 MB/meeting × 10 = **80 MB/day** = 2.4 GB/month

**After (with cloud recording enabled):**
- Raw tracks: 6 MB/meeting
- Processed MP3: 2 MB/meeting
- Cloud MP4: 30 min × 38 MB/min = 1,140 MB/meeting
- Total: 1,148 MB/meeting × 10 = **11.5 GB/day** = 345 GB/month

**S3 Cost (us-east-1 standard):**
- Storage: $0.023/GB/month
- Before: 2.4 GB/month = **$0.06/month**
- After: 345 GB/month = **$7.94/month**

**Daily.co cost:** Check pricing page for cloud recording charges (separate from raw-tracks)

**Recommendation:**
- Consider lifecycle policy for cloud MP4s (e.g., delete after 90 days if not accessed)
- Monitor actual usage and adjust retention as needed

---

## Timeline Estimate

**Phase 0 (Preparation):** 2-4 hours
- Prototype instanceId approach
- Remove dead code
- Update frontend recording start

**Phase 1 (Database):** 1 hour
- Migration, model updates, verification

**Phase 2 (API Client):** 1 hour
- Add start_recording methods, type checks

**Phase 3 (Backend Endpoint):** 2 hours
- Create meetings router, endpoint implementation

**Phase 4 (Webhook Handler):** 2 hours
- Update _handle_recording_ready, type discrimination

**Phase 5 (Meeting API):** 1 hour
- Schema updates, response updates

**Phase 6 (Frontend Display):** 2 hours
- Transcript page updates (cloud recording player)

**Phase 7 (Testing):** 4 hours
- End-to-end manual test
- Multi-participant validation
- Alternative approach if needed

**Total:** ~15-17 hours (2 days)

**Buffer for issues:** +4 hours (lock implementation if needed, debugging)

**Realistic estimate:** 2-3 days

---

## Appendix: Key Daily.co Documentation

- [Recording calls with the Daily API](https://docs.daily.co/guides/products/live-streaming-recording/recording-calls-with-the-daily-api)
- [startRecording() - Daily.js](https://docs.daily.co/reference/daily-js/instance-methods/start-recording)
- [POST /rooms/:name/recordings/start](https://docs.daily.co/reference/rest-api/rooms/recordings/start)
- [Multi-instance recording](https://docs.daily.co/guides/products/live-streaming-recording/multi-instance-live-streaming-recording)
- [Webhooks - recording.ready-to-download](https://docs.daily.co/reference/rest-api/webhooks/events/recording-ready-to-download)
