# Codebase Review Guide: Audio Storage Consent Implementation

This guide walks through the relevant parts of the codebase for implementing the audio storage consent flow. **Important**: This implementation works with post-processing deletion, not real-time recording control, due to Whereby integration constraints.

## System Reality: Recording Detection Constraints

**Critical Understanding**: 
- **No real-time recording detection** - System only discovers recordings after they complete via SQS polling (60+ second delay)
- **Cannot stop recordings in progress** - Whereby controls recording entirely based on room configuration  
- **Limited webhooks** - Only `room.client.joined/left` events available, no recording events
- **Post-processing intervention only** - Can only mark recordings for deletion during SQS processing

## 1. Current Consent Implementation (TO BE REMOVED)

### File: `www/app/[roomName]/page.tsx`
**Purpose:** Room entry page with blocking consent dialog

**Key Areas:**
- **Line 24:** `const [consentGiven, setConsentGiven] = useState<boolean | null>(null);`
- **Lines 34-36:** `handleConsent` function that sets consent state
- **Lines 80-124:** Consent UI blocking room entry
- **Line 80:** `if (!isAuthenticated && !consentGiven)` - blocking condition

**Current Logic:**
```typescript
// Lines 99-111: Consent request UI
{consentGiven === null ? (
  <>
    <Text fontSize="lg" fontWeight="bold">
      This meeting may be recorded. Do you consent to being recorded?
    </Text>
    <HStack spacing={4}>
      <Button variant="outline" onClick={() => handleConsent(false)}>
        No, I do not consent
      </Button>
      <Button colorScheme="blue" onClick={() => handleConsent(true)}>
        Yes, I consent
      </Button>
    </HStack>
  </>
) : (
  // Lines 114-120: Rejection message
  <Text>You cannot join the meeting without consenting...</Text>
)}
```

**What to Change:** Remove entire consent blocking logic, allow direct room entry.

---

## 2. Whereby Integration Reality

### File: `www/app/[roomName]/page.tsx` 
**Purpose:** Main room page where video call happens via whereby-embed

**Key Whereby Integration:**
- **Line 129:** `<whereby-embed>` element - this IS the video call
- **Lines 26-28:** Room URL from meeting API
- **Lines 48-57:** Event listeners for whereby events

**What Happens:**
1. `useRoomMeeting()` calls backend to create/get Whereby meeting
2. Whereby automatically records based on room `recording_trigger` configuration
3. **NO real-time recording status** - system doesn't know when recording starts/stops

### File: `www/app/[roomName]/useRoomMeeting.tsx`
**Purpose:** Creates or retrieves Whereby meeting for room

**Key Flow:**
- **Line 48:** Calls `v1RoomsCreateMeeting({ roomName })`
- **Lines 49-52:** Returns meeting with `room_url` and `host_room_url`
- Meeting includes recording configuration from room settings

**What to Add:** Consent dialog overlay on the whereby-embed - always ask for consent regardless of meeting configuration (simplified approach).

---

## 3. Recording Discovery System (POST-PROCESSING ONLY)

### File: `server/reflector/worker/process.py`
**Purpose:** Discovers recordings after they complete via SQS polling

**Key Areas:**
- **Lines 24-62:** `process_messages()` - polls SQS every 60 seconds
- **Lines 66-133:** `process_recording()` - processes discovered recording files
- **Lines 69-71:** Extracts meeting info from S3 object key format

**Current Discovery Flow:**
```python
# Lines 69-71: Parse S3 object key
room_name = f"/{object_key[:36]}"  # First 36 chars = room GUID
recorded_at = datetime.fromisoformat(object_key[37:57])  # Timestamp

# Lines 73-74: Link to meeting
meeting = await meetings_controller.get_by_room_name(room_name)
room = await rooms_controller.get_by_id(meeting.room_id)
```

**What to Add:** Consent checking after transcript processing - always create transcript first, then delete only audio files if consent denied.

### File: `server/reflector/worker/app.py`
**Purpose:** Celery task scheduling

**Key Schedule:**
- **Lines 26-29:** `process_messages` runs every 60 seconds
- **Lines 30-33:** `process_meetings` runs every 60 seconds to check meeting status

**Reality:** consent must be requested during the meeting, not based on recording detection.

---

## 4. Meeting-Based Consent Timing

### File: `server/reflector/views/whereby.py`
**Purpose:** Whereby webhook handler - receives participant join/leave events

**Key Areas:**
- **Lines 69-72:** Handles `room.client.joined` and `room.client.left` events
- **Line 71:** Updates `num_clients` count in meeting record

**Current Logic:**
```python
# Lines 69-72: Participant tracking
if event.type in ["room.client.joined", "room.client.left"]:
    await meetings_controller.update_meeting(
        meeting.id, num_clients=event.data["numClients"]
    )
```

**What to Add:** ALWAYS ask for consent - no triggers, no conditions. Simple list field to track who denied consent.

### File: `server/reflector/db/meetings.py`
**Purpose:** Meeting database model and recording configuration

**Key Recording Config:**
- **Lines 56-59:** Recording trigger options:
  - `"automatic"` - Recording starts immediately
  - `"automatic-2nd-participant"` (default) - Recording starts when 2nd person joins
  - `"prompt"` - Manual recording start
  - `"none"` - No recording

**Current Meeting Model:**
```python
# Lines 56-59: Recording configuration
recording_type: Literal["none", "local", "cloud"] = "cloud"
recording_trigger: Literal[
    "none", "prompt", "automatic", "automatic-2nd-participant"
] = "automatic-2nd-participant"
```

**What to Add:** Dictionary field `participant_consent_responses: dict[str, bool]` in Meeting model to store {user_id: true/false}. ALWAYS ask for consent - no complex logic.

---

## 5. Consent Implementation (NO WebSockets Needed)

**Consent is meeting-level, not transcript-level** - WebSocket events are for transcript processing, not consent.

### Simple Consent Flow:
1. **Frontend**: Show consent dialog when meeting loads
2. **User Response**: Direct API call to `/meetings/{meeting_id}/consent`  
3. **Backend**: Store response in meeting record
4. **SQS Processing**: Check consent during recording processing

**No WebSocket events needed** - consent is a simple API interaction, not real-time transcript data.

---

## 4. Backend WebSocket System

### File: `server/reflector/views/transcripts_websocket.py`
**Purpose:** Server-side WebSocket endpoint for real-time events

**Key Areas:**
- **Lines 19-55:** `transcript_events_websocket` function
- **Line 32:** Room ID format: `room_id = f"ts:{transcript_id}"`
- **Lines 37-44:** Initial event sending to new connections
- **Lines 42-43:** Filtering events: `if name in ("TRANSCRIPT", "STATUS"): continue`

**Current Flow:**
1. WebSocket connects to `/transcripts/{transcript_id}/events`
2. Server adds user to Redis room `ts:{transcript_id}`
3. Server sends historical events (except TRANSCRIPT/STATUS)
4. Server waits for new events via Redis pub/sub

**What to Add:** Handle new consent events in the message flow.

### File: `server/reflector/ws_manager.py`
**Purpose:** Redis pub/sub WebSocket management

**Key Areas:**
- **Lines 61-99:** `WebsocketManager` class
- **Lines 78-79:** `send_json` method for broadcasting
- **Lines 88-98:** `_pubsub_data_reader` for distributing messages

**Broadcasting Pattern:**
```python
# Line 78: How to broadcast to all users in a room
async def send_json(self, room_id: str, message: dict) -> None:
    await self.pubsub_client.send_json(room_id, message)
```

**What to Use:** This system for broadcasting consent requests and responses.

---

## 5. Database Models and Migrations

### File: `server/reflector/db/transcripts.py`
**Purpose:** Transcript database model and controller

**Key Areas:**
- **Lines 28-73:** `transcripts` SQLAlchemy table definition
- **Lines 149-172:** `Transcript` Pydantic model
- **Lines 304-614:** `TranscriptController` class with database operations

**Current Schema Fields:**
```python
# Lines 31-72: Key existing columns
sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
sqlalchemy.Column("status", sqlalchemy.String),
sqlalchemy.Column("duration", sqlalchemy.Integer),
sqlalchemy.Column("locked", sqlalchemy.Boolean),
sqlalchemy.Column("audio_location", sqlalchemy.String, server_default="local"),
# ... more columns
```

**Audio File Management:**
- **Lines 225-230:** Audio file path properties
- **Lines 252-284:** `get_audio_url` method for accessing audio
- **Lines 554-571:** `move_mp3_to_storage` for cloud storage

**What to Add:** New columns for consent tracking and deletion marking.

### File: `server/migrations/versions/b9348748bbbc_reviewed.py`
**Purpose:** Example migration pattern for adding boolean columns

**Pattern:**
```python
# Lines 20-23: Adding boolean column with default
def upgrade() -> None:
    op.add_column('transcript', sa.Column('reviewed', sa.Boolean(), 
                 server_default=sa.text('0'), nullable=False))

def downgrade() -> None:
    op.drop_column('transcript', 'reviewed')
```

**What to Follow:** This pattern for adding consent columns.

---

## 6. API Endpoint Patterns

### File: `server/reflector/views/transcripts.py`
**Purpose:** REST API endpoints for transcript operations

**Key Areas:**
- **Lines 29-30:** Router setup: `router = APIRouter()`
- **Lines 70-85:** `CreateTranscript` and `UpdateTranscript` models
- **Lines 122-135:** Example POST endpoint: `transcripts_create`

**Endpoint Pattern:**
```python
# Lines 122-135: Standard endpoint structure
@router.post("/transcripts", response_model=GetTranscript)
async def transcripts_create(
    info: CreateTranscript,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    return await transcripts_controller.add(...)
```

**Authentication Pattern:**
- **Line 125:** Optional user authentication dependency
- **Line 127:** Extract user ID: `user_id = user["sub"] if user else None`

**What to Follow:** This pattern for new consent endpoint.

---

## 7. Live Pipeline System

### File: `server/reflector/pipelines/main_live_pipeline.py`
**Purpose:** Real-time processing pipeline during recording

**Key Areas:**
- **Lines 80-96:** `@broadcast_to_sockets` decorator for WebSocket events
- **Lines 98-104:** `@get_transcript` decorator for database access
- **Line 56:** WebSocket manager import: `from reflector.ws_manager import get_ws_manager`

**Event Broadcasting Pattern:**
```python
# Lines 80-95: Decorator for broadcasting events
def broadcast_to_sockets(func):
    async def wrapper(self, *args, **kwargs):
        resp = await func(self, *args, **kwargs)
        if resp is None:
            return
        await self.ws_manager.send_json(
            room_id=self.ws_room_id,
            message=resp.model_dump(mode="json"),
        )
    return wrapper
```

---

## 8. Modal/Dialog Patterns

### File: `www/app/(app)/transcripts/[transcriptId]/shareModal.tsx`
**Purpose:** Example modal implementation using fixed overlay

**Key Areas:**
- **Lines 105-176:** Modal implementation using `fixed inset-0` overlay
- **Lines 107-108:** Overlay styling: `fixed inset-0 bg-gray-600 bg-opacity-50`
- **Lines 152-170:** Button patterns for actions

**Modal Structure:**
```typescript
// Lines 105-109: Modal overlay and container
<div className="absolute">
  {props.show && (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 w-96 shadow-lg rounded-md bg-white">
        // Modal content...
      </div>
    </div>
  )}
</div>
```

### File: `www/app/(app)/transcripts/shareAndPrivacy.tsx`
**Purpose:** Example using Chakra UI Modal components

**Key Areas:**
- **Lines 10-16:** Chakra UI Modal imports
- **Lines 86-100:** Chakra Modal structure

**Chakra Modal Pattern:**
```typescript
// Lines 86-94: Chakra UI Modal structure
<Modal isOpen={!!showModal} onClose={() => setShowModal(false)} size={"xl"}>
  <ModalOverlay />
  <ModalContent>
    <ModalHeader>Share</ModalHeader>
    <ModalBody>
      // Modal content...
    </ModalBody>
  </ModalContent>
</Modal>
```

**What to Choose:** Either pattern works - fixed overlay for simple cases, Chakra UI for consistent styling.

---

## 9. Audio File Management

### File: `server/reflector/db/transcripts.py`
**Purpose:** Audio file storage and access

**Key Methods:**
- **Lines 225-230:** File path properties
  - `audio_wav_filename`: Local WAV file path
  - `audio_mp3_filename`: Local MP3 file path  
  - `storage_audio_path`: Cloud storage path
- **Lines 252-284:** `get_audio_url()` - Generate access URL
- **Lines 554-571:** `move_mp3_to_storage()` - Move to cloud
- **Lines 572-580:** `download_mp3_from_storage()` - Download from cloud

**File Path Properties:**
```python
# Lines 225-230: Audio file locations
@property
def audio_wav_filename(self):
    return self.data_path / "audio.wav"

@property  
def audio_mp3_filename(self):
    return self.data_path / "audio.mp3"
```

**Storage Logic:**
- **Line 253:** Local files: `if self.audio_location == "local"`
- **Line 255:** Cloud storage: `elif self.audio_location == "storage"`

**What to Modify:** Add deletion logic and update `get_audio_url` to handle deleted files.

---

## 10. Review Checklist

Before implementing, manually review these areas with the **meeting-based consent** approach:

### Frontend Changes
- [ ] **Room Entry**: Remove consent blocking in `www/app/[roomName]/page.tsx:80-124`
- [ ] **Meeting UI**: Add consent dialog overlay on `whereby-embed` in `www/app/[roomName]/page.tsx:126+`
- [ ] **Meeting Hook**: Update `www/app/[roomName]/useRoomMeeting.tsx` to provide meeting data for consent
- [ ] **WebSocket Events**: Add consent event handlers (meeting-based, not transcript-based)
- [ ] **User Identification**: Add browser fingerprinting for anonymous users

### Backend Changes - Meeting Scope
- [ ] **Database**: Create `meeting_consent` table migration following `server/migrations/versions/b9348748bbbc_reviewed.py` pattern
- [ ] **Meeting Model**: Add consent tracking in `server/reflector/db/meetings.py`
- [ ] **Recording Model**: Add deletion flags in `server/reflector/db/recordings.py`
- [ ] **API**: Add meeting consent endpoint in `server/reflector/views/meetings.py`
- [ ] **Whereby Webhook**: Update `server/reflector/views/whereby.py` to trigger consent based on participant count
- [ ] **SQS Processing**: Update `server/reflector/worker/process.py` to check consent before processing recordings

### Critical Integration Points
- [ ] **Consent Timing**: ALWAYS ask for consent - no conditions, no triggers, no participant count checks
- [ ] **SQS Processing**: Always create transcript first, then delete only audio files if consent denied
- [ ] **Meeting Scoping**: All consent tracking uses `meeting_id`, not `room_id` (rooms are reused)
- [ ] **Post-Processing Only**: No real-time recording control - all intervention happens during SQS processing

### Testing Strategy
- [ ] **Multiple Participants**: Test consent collection from multiple users in same meeting
- [ ] **Room Reuse**: Verify consent doesn't affect other meetings in same room
- [ ] **Recording Triggers**: Test different `recording_trigger` configurations
- [ ] **SQS Deletion**: Verify recordings are deleted from S3 when consent denied
- [ ] **Timing Edge Cases**: Test consent given after recording already started

**Reality Check**: This implementation works with **post-processing deletion only**. We cannot stop recordings in progress or detect exactly when they start. Consent timing is estimated based on meeting configuration and participant events.