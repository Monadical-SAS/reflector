# Audio Storage Consent Implementation Plan

## Overview
Move consent from room entry to during recording, asking specifically about audio storage while allowing transcription to continue regardless of response.

## Implementation Phases

### Phase 1: Database Schema Changes

**Meeting Consent Table:** `server/migrations/versions/[timestamp]_add_meeting_consent_table.py`

Create new table for meeting-scoped consent (rooms are reused, consent is per-meeting):

```python
def upgrade() -> None:
    op.create_table('meeting_consent',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('meeting_id', sa.String(), nullable=False),
        sa.Column('user_identifier', sa.String(), nullable=False),  # IP, session, or user ID
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('consent_timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['meeting_id'], ['meeting.id']),
    )
```

**Update Models:** `server/reflector/db/meetings.py` and `server/reflector/db/recordings.py`

```python
# New model for meeting consent
class MeetingConsent(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    meeting_id: str
    user_identifier: str
    consent_given: bool
    consent_timestamp: datetime
    user_agent: str | None = None
```

### Phase 2: Backend API Changes

**New Consent Endpoint:** `server/reflector/views/meetings.py`

Meeting-based consent endpoint (since consent is per meeting session):

```python
class MeetingConsentRequest(BaseModel):
    consent_given: bool
    user_identifier: str  # IP, session ID, or user ID
    
@router.post("/meetings/{meeting_id}/consent")
async def meeting_audio_consent(
    meeting_id: str,
    request: MeetingConsentRequest,
    user_request: Request,
):
    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    # Store consent in meeting_consent table
    consent = MeetingConsent(
        meeting_id=meeting_id,
        user_identifier=request.user_identifier,
        consent_given=request.consent_given,
        consent_timestamp=datetime.utcnow(),
        user_agent=user_request.headers.get("user-agent")
    )
    
    await meeting_consent_controller.create(consent)
    
    # Broadcast consent event via WebSocket to room participants
    ws_manager = get_ws_manager()
    await ws_manager.send_json(
        room_id=f"meeting:{meeting_id}",
        message={
            "event": "CONSENT_RESPONSE",
            "data": {
                "meeting_id": meeting_id,
                "consent_given": request.consent_given,
                "user_identifier": request.user_identifier
            }
        }
    )
    
    return {"status": "success", "consent_id": consent.id}
```

### Phase 3: WebSocket Event System

**Consent Communication:** Use direct API calls instead of WebSocket events

Since consent is meeting-level (not transcript-level), use direct API calls:
- Frontend shows consent dialog immediately when meeting loads
- User response sent directly to `/meetings/{meeting_id}/consent` endpoint
- No need for new WebSocket events - keep it simple

**Consent Request:** ALWAYS ask - no conditions

```ts
# Frontend: Show consent dialog immediately when meeting loads
useEffect(() => {
  if (meeting?.id) {
    // ALWAYS show consent dialog - no conditions
    showConsentDialog(meeting.id);
  }
}, [meeting?.id]);

# Backend: Consent storage in meeting record
# Add to Meeting model:
participant_consent_responses: dict[str, bool] = Field(default_factory=dict)  # {user_id: true/false}
```

**Simple Consent Storage:** Track participant responses

```python
# Update Meeting model to include:
participant_consent_responses: dict[str, bool] = Field(default_factory=dict)

# Note that it must not be possible to call /consent on already finished meeting.
# Consent endpoint stores the response:
@router.post("/meetings/{meeting_id}/consent")
async def meeting_audio_consent(meeting_id: str, request: MeetingConsentRequest):
    meeting = await meetings_controller.get_by_id(meeting_id)
    
    # Store the consent response (true/false)
    # Only store if they actually clicked something
    consent_responses = meeting.participant_consent_responses or {}
    consent_responses[request.user_identifier] = request.consent_given
    
    await meetings_controller.update_meeting(
        meeting_id, participant_consent_responses=consent_responses
    )
    
    return {"status": "success"}
```

### Phase 4: Frontend Changes

**Remove Room Entry Consent:** `www/app/[roomName]/page.tsx`

Remove lines 24, 34-36, 80-124:
```typescript
// Remove these lines:
const [consentGiven, setConsentGiven] = useState<boolean | null>(null);
const handleConsent = (consent: boolean) => { setConsentGiven(consent); };
// Remove entire consent UI block (lines 80-124)

// Simplify render condition:
if (!isAuthenticated) {
  // Show loading or direct room entry, no consent check
}
```

**Add Consent Dialog Component:** `www/app/(app)/transcripts/components/AudioConsentDialog.tsx`

Based on `shareModal.tsx` patterns:

```typescript
interface AudioConsentDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onConsent: (given: boolean) => void;
}

const AudioConsentDialog = ({ isOpen, onClose, onConsent }: AudioConsentDialogProps) => {
  return (
    <Modal isOpen={isOpen} onClose={onClose} closeOnOverlayClick={false}>
      <ModalOverlay />
      <ModalContent>
        <ModalHeader>Audio Storage Consent</ModalHeader>
        <ModalBody>
          <Text mb={4}>
            Do you consent to storing this audio recording? 
            The transcript will be generated regardless of your choice.
          </Text>
          <HStack spacing={4}>
            <Button colorScheme="green" onClick={() => onConsent(true)}>
              Yes, store the audio
            </Button>
            <Button colorScheme="red" onClick={() => onConsent(false)}>
              No, delete after transcription
            </Button>
          </HStack>
        </ModalBody>
      </ModalContent>
    </Modal>
  );
};
```

**Update Recording Interface:** `www/app/(app)/transcripts/[transcriptId]/record/page.tsx`

Add consent dialog state and handling:

```typescript
const [showConsentDialog, setShowConsentDialog] = useState(false);
const [consentStatus, setConsentStatus] = useState<string>('');

// Add to existing WebSocket event handlers
const handleConsentRequest = () => {
  setShowConsentDialog(true);
};

const handleConsentResponse = async (consentGiven: boolean) => {
  // Call API endpoint
  await api.v1TranscriptAudioConsent({
    transcriptId: details.params.transcriptId,
    requestBody: { consent_given: consentGiven }
  });
  setShowConsentDialog(false);
  setConsentStatus(consentGiven ? 'given' : 'denied');
};
```


### Phase 5: SQS Processing Integration

**Consent Check During Recording Processing:** `server/reflector/worker/process.py`

Update `process_recording()` to check consent before processing:

```python
@shared_task
@asynctask
async def process_recording(bucket_name: str, object_key: str):
    logger.info("Processing recording: %s/%s", bucket_name, object_key)

    # Extract meeting info from S3 object key
    room_name = f"/{object_key[:36]}"
    recorded_at = datetime.fromisoformat(object_key[37:57])

    meeting = await meetings_controller.get_by_room_name(room_name)

    
    recording = await recordings_controller.get_by_object_key(bucket_name, object_key)
    if not recording:
        recording = await recordings_controller.create(
            Recording(
                bucket_name=bucket_name,
                object_key=object_key,
                recorded_at=recorded_at,
                meeting_id=meeting.id
            )
        )
    
    # ALWAYS create transcript first (regardless of consent)
    transcript = await transcripts_controller.get_by_recording_id(recording.id)
    if transcript:
        await transcripts_controller.update(transcript, {"topics": []})
    else:
        transcript = await transcripts_controller.add(
            "", source_kind=SourceKind.ROOM, source_language="en", 
            target_language="en", user_id=room.user_id, 
            recording_id=recording.id, share_mode="public"
        )
    
    # Process transcript normally (transcription, topics, summaries)
    _, extension = os.path.splitext(object_key)
    upload_filename = transcript.data_path / f"upload{extension}"
    # ... continue with full transcript processing ...
    # Check if any participant denied consent (check dict values)
    consent_responses = meeting.participant_consent_responses or {}
    should_delete = any(consent is False for consent in consent_responses.values())
    # AFTER transcript processing is complete, delete audio if consent denied
    if should_delete:
        logger.info(f"Deleting audio files for {object_key} due to consent denial")
        await delete_audio_files_only(transcript, bucket_name, object_key)

```

**Audio Deletion Function (AFTER transcript processing):**

```python
async def delete_audio_files_only(transcript: Transcript, bucket_name: str, object_key: str):
    """Delete ONLY audio files from all locations, keep transcript data"""
    
    try:
        # 1. Delete original Whereby recording from S3
        s3_whereby = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_WHEREBY_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
        )
        s3_whereby.delete_object(Bucket=bucket_name, Key=object_key)
        logger.info(f"Deleted original Whereby recording: {bucket_name}/{object_key}")
        
        # 2. Delete processed audio from transcript storage S3 bucket
        if transcript.audio_location == "storage":
            storage = get_storage()
            await storage.delete_file(transcript.storage_audio_path)
            logger.info(f"Deleted processed audio from storage: {transcript.storage_audio_path}")
        
        # 3. Delete local audio files (if any remain)
        transcript.audio_mp3_filename.unlink(missing_ok=True)
        transcript.audio_wav_filename.unlink(missing_ok=True)
        (transcript.data_path / "upload.mp4").unlink(missing_ok=True)
        
        # 4. Update transcript to reflect audio deletion (keep all other data)
        await transcripts_controller.update(transcript, {
            'audio_location_deleted': True
        })
        
        logger.info(f"Deleted all audio files for transcript {transcript.id}, kept transcript data")
        
    except Exception as e:
        logger.error(f"Failed to delete audio files for {object_key}: {str(e)}")
```

**Meeting Consent Controller:** `server/reflector/db/meeting_consent.py`


```python
class MeetingConsentController:
    async def create(self, consent: MeetingConsent):
        query = meeting_consent.insert().values(**consent.model_dump())
        await database.execute(query)
        return consent
    
    async def get_by_meeting_id(self, meeting_id: str) -> list[MeetingConsent]:
        query = meeting_consent.select().where(meeting_consent.c.meeting_id == meeting_id)
        results = await database.fetch_all(query)
        return [MeetingConsent(**result) for result in results]
    
    async def has_any_denial(self, meeting_id: str) -> bool:
        """Check if any participant denied consent for this meeting"""
        query = meeting_consent.select().where(
            meeting_consent.c.meeting_id == meeting_id,
            meeting_consent.c.consent_given == False
        )
        result = await database.fetch_one(query)
        return result is not None
```

### Phase 6: Testing Strategy

**Unit Tests:**
- Test consent API endpoint
- Test WebSocket event broadcasting
- Test audio deletion logic
- Test consent status tracking

**Integration Tests:**
- Test full consent flow during recording
- Test multiple participants consent handling
- Test recording continuation regardless of consent
- Test audio file cleanup

**Manual Testing:**
- Join room without consent (should work)
- Receive consent request during recording
- Verify transcription continues regardless of consent choice
- Verify audio deletion when consent denied
- Verify audio preservation when consent given

### Phase 7: Deployment Considerations

**Database Migration:**
```bash
# Run migration
alembic upgrade head
```

**Rollback Plan:**
- Keep old consent logic in feature flag
- Database migration includes downgrade function
- Frontend can toggle between old/new consent flows

**Monitoring:**
- Track consent request rates
- Monitor audio deletion operations  
- Alert on consent-related errors

## Implementation Order

1. **Database migration** - Foundation for all changes
2. **Backend API endpoints** - Core consent handling logic
3. **WebSocket event system** - Real-time consent communication
4. **Remove room entry consent** - Unblock room joining
5. **Add recording consent dialog** - New consent UI
6. **Audio deletion logic** - Cleanup mechanism
7. **Testing and deployment** - Validation and rollout

## Risk Mitigation

- **Feature flags** for gradual rollout
- **Comprehensive logging** for consent operations
- **Rollback plan** if consent flow breaks
- **Audio file backup** before deletion (configurable)
- **Legal review** of consent language and timing

This plan maintains backward compatibility while implementing the new consent flow without interrupting core recording functionality.

## Extra notes

Room creator must not be asked for consent