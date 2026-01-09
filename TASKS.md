# TASKS: Dual Recording Support (Cloud + Raw-Tracks)

## Overview

Tasks extracted from PRD.md for implementing simultaneous Daily.co cloud recording (MP4) and raw-tracks recording (per-participant WebM).

---

## Phase 0: Preparation & Validation

### Task 0.1: Prototype instanceId approach ⚠️ BLOCKER

**Priority:** MUST DO FIRST (blocks all implementation)

**Goal:** Validate Daily.co behavior with same/different instanceId for cloud + raw-tracks

**Steps:**
1. Create test script `server/scripts/test_daily_dual_recording.py`
2. Test 1: Same instanceId for both cloud and raw-tracks
3. Test 2: Multiple start calls (simulate multiple participants)
4. Test 3: Different instanceIds (fallback if same fails)
5. Document findings in `server/DAILYCO_TEST.md`
6. Update PRD if different approach needed

**Acceptance Criteria:**
- [ ] Know which instanceId strategy works
- [ ] Know if Daily.co handles duplicate start calls gracefully
- [ ] Documented in DAILYCO_TEST.md with recommendation
- [ ] Decision made: proceed with same instanceId OR different instanceIds

**Files:** `server/scripts/test_daily_dual_recording.py`, `server/DAILYCO_TEST.md`

**References:** PRD lines 100-132

---

### Task 0.2: Remove dead JWT start_cloud_recording code

**Priority:** High (cleanup before adding new features)

**Goal:** Remove unused JWT `start_cloud_recording` parameter that's been dead code

**Changes:**
1. `server/reflector/video_platforms/daily.py`:
   - Remove `start_cloud_recording` parameter from `create_meeting_token()`
   - Remove `max_recording_duration_seconds` parameter
   - Remove `start_cloud_recording_opts` logic
   - Update `MeetingTokenProperties` instantiation

2. `server/reflector/views/rooms.py`:
   - Update `create_meeting_token()` call site (around line 589)
   - Remove `start_cloud_recording=meeting.recording_type == "cloud"` argument
   - Remove `max_recording_duration_seconds` argument

**Acceptance Criteria:**
- [ ] `start_cloud_recording` parameter removed from method signature
- [ ] `max_recording_duration_seconds` parameter removed
- [ ] `start_cloud_recording_opts` logic removed
- [ ] Call site in `rooms.py` updated
- [ ] Type checking passes: `cd server && uv run mypy reflector/video_platforms/daily.py reflector/views/rooms.py`
- [ ] No errors

**Files:** `server/reflector/video_platforms/daily.py`, `server/reflector/views/rooms.py`

**References:** PRD lines 134-218

---

### Task 0.3: Update frontend recording start logic

**Priority:** High (foundation for dual recording)

**Goal:** Change frontend to start cloud recording via daily-js and trigger backend for raw-tracks

**Changes:**
1. `www/app/[roomName]/components/DailyRoom.tsx`:
   - Add `useState` for `recordingInstanceId` (crypto.randomUUID())
   - Update `handleFrameJoinMeeting` callback:
     - Change `type: "raw-tracks"` to `type: "cloud"`
     - Add `instanceId` parameter to startRecording
     - Add fetch call to backend `/v1/meetings/${meeting.id}/recordings/start`
     - Pass same instanceId to backend
   - Update dependencies array

**Acceptance Criteria:**
- [ ] recordingInstanceId generated once per component mount
- [ ] Cloud recording started via daily-js with instanceId
- [ ] Backend endpoint called with type="raw-tracks" and same instanceId
- [ ] Error handling for backend call
- [ ] Console logging shows both actions
- [ ] Type checking passes: `cd www && pnpm tsc --noEmit`

**Files:** `www/app/[roomName]/components/DailyRoom.tsx`

**References:** PRD lines 220-289

---

## Phase 1: Database Schema

### Task 1.1: Add cloud recording fields to Meeting table

**Priority:** High (required for data storage)

**Goal:** Add database columns to store cloud recording S3 key and duration

**Steps:**
1. Generate migration: `cd server && uv run alembic revision --autogenerate -m "add cloud recording support"`
2. Verify migration adds:
   - `meeting.cloud_recording_s3_key` (String, nullable)
   - `meeting.cloud_recording_duration` (Integer, nullable)
3. Run migration: `cd server && uv run alembic upgrade head`
4. Verify columns exist in database

**Acceptance Criteria:**
- [ ] Migration file created in `server/reflector/db/migrations/versions/`
- [ ] Migration adds `cloud_recording_s3_key` column
- [ ] Migration adds `cloud_recording_duration` column
- [ ] Migration runs without errors
- [ ] Verification query shows columns: `docker compose exec postgres psql -U reflector -d reflector -c "\d meeting" | grep cloud_recording`
- [ ] Both columns visible in output

**Files:** `server/reflector/db/migrations/versions/<timestamp>_add_cloud_recording_support.py`

**References:** PRD lines 291-343

---

### Task 1.2: Update DB models with cloud recording fields

**Priority:** High (required after migration)

**Goal:** Add cloud recording fields to SQLAlchemy table and Pydantic model

**Changes:**
1. `server/reflector/db/meetings.py`:
   - Add columns to `meetings` table definition (~line 14):
     - `sa.Column("cloud_recording_s3_key", sa.String, nullable=True)`
     - `sa.Column("cloud_recording_duration", sa.Integer, nullable=True)`
   - Add fields to `Meeting` model (~line 94):
     - `cloud_recording_s3_key: str | None = None`
     - `cloud_recording_duration: int | None = None`

**Acceptance Criteria:**
- [ ] Table definition includes both new columns
- [ ] Model includes both new fields with proper types
- [ ] Type checking passes: `cd server && uv run mypy reflector/db/meetings.py`

**Files:** `server/reflector/db/meetings.py`

**References:** PRD lines 345-395

---

## Phase 2: Daily.co API Client Extension

### Task 2.1: Add start_recording method to Daily.co API client

**Priority:** Medium (foundation for backend endpoint)

**Goal:** Add REST API method to start recordings via Daily.co API

**Changes:**
1. `server/reflector/dailyco_api/client.py`:
   - Add `start_recording()` method after `list_recordings()`
   - Parameters: `room_name`, `recording_type` (Literal["cloud", "raw-tracks"]), `instance_id`
   - POST to `/rooms/{room_name}/recordings/start`
   - Return response via `_handle_response()`
   - Add docstring with reference to Daily.co docs

**Acceptance Criteria:**
- [ ] Method signature: `async def start_recording(self, room_name: str, recording_type: Literal["cloud", "raw-tracks"], instance_id: str) -> dict`
- [ ] POSTs to correct endpoint with JSON body
- [ ] Docstring includes Daily.co docs link
- [ ] Type checking passes: `cd server && uv run mypy reflector/dailyco_api/client.py`

**Files:** `server/reflector/dailyco_api/client.py`

**References:** PRD lines 397-443

---

### Task 2.2: Expose start_recording in DailyClient wrapper

**Priority:** Medium (required for views layer)

**Goal:** Add proxy method in DailyClient to call Daily.co API client

**Changes:**
1. `server/reflector/video_platforms/daily.py`:
   - Add `start_recording()` method after `create_meeting_token()`
   - Proxy call to `self._api_client.start_recording()`
   - Same parameters and return type

**Acceptance Criteria:**
- [ ] Method added with same signature as Task 2.1
- [ ] Proxies call to `_api_client.start_recording()`
- [ ] Docstring explains purpose
- [ ] Type checking passes: `cd server && uv run mypy reflector/video_platforms/daily.py`

**Files:** `server/reflector/video_platforms/daily.py`

**References:** PRD lines 445-475

---

## Phase 3: Backend Endpoint for Raw-Tracks Start

### Task 3.1: Create meetings API endpoint for recording start

**Priority:** High (required for frontend integration)

**Goal:** Create backend endpoint for frontend to trigger raw-tracks recording

**Steps:**
1. Create new file `server/reflector/views/meetings.py`
2. Implement two endpoints:
   - `POST /meetings/{meeting_id}/recordings/start` - Start raw-tracks via Daily.co REST API
   - `GET /meetings/{meeting_id}/cloud-recording` - Serve cloud recording MP4 (presigned URL)
3. Register router in `server/reflector/app.py`

**Acceptance Criteria:**
- [ ] POST endpoint validates meeting exists (404 if not)
- [ ] POST endpoint validates type="raw-tracks" (400 if cloud)
- [ ] POST endpoint calls Daily.co API with instanceId
- [ ] POST endpoint logs success/failure
- [ ] GET endpoint returns 307 redirect to S3 presigned URL
- [ ] GET endpoint returns 404 if no cloud recording
- [ ] Router registered with prefix `/v1/meetings`
- [ ] Type checking passes: `cd server && uv run mypy reflector/views/meetings.py reflector/app.py`
- [ ] No authentication required (anonymous users supported)

**Files:** `server/reflector/views/meetings.py` (NEW), `server/reflector/app.py`

**References:** PRD lines 477-590

---

## Phase 4: Webhook Handler Updates

### Task 4.1: Update recording.ready-to-download webhook handler

**Priority:** High (required for data persistence)

**Goal:** Handle both cloud and raw-tracks webhooks, store cloud recording metadata

**Changes:**
1. `server/reflector/views/daily.py`:
   - Replace `_handle_recording_ready()` function (~line 174)
   - Add logic to discriminate by `event.payload.type`:
     - `"cloud"`: Store S3 key and duration in meeting table
     - `"raw-tracks"`: Queue multitrack processing (existing behavior)
   - Add logging for both paths

**Acceptance Criteria:**
- [ ] Cloud recording: stores `cloud_recording_s3_key` and `cloud_recording_duration` in meeting table
- [ ] Cloud recording: logs meeting_id, s3_key, duration
- [ ] Raw-tracks: queues `process_multitrack_recording` task (unchanged from existing code)
- [ ] Raw-tracks: logs recording_id, room_name, num_tracks (unchanged from existing code)
- [ ] Unknown types: log warning
- [ ] Type checking passes: `cd server && uv run mypy reflector/views/daily.py`

**Files:** `server/reflector/views/daily.py`

**References:** PRD lines 592-690

---

## Phase 5: Meeting API Updates

### Task 5.1: Add cloud recording info to Meeting API response

**Priority:** Medium (required for frontend display)

**Goal:** Expose cloud recording availability and duration in meeting response

**Changes:**
1. `server/reflector/views/rooms.py`:
   - Update `Meeting` response schema (~line 55):
     - Add `cloud_recording_available: bool = False`
     - Add `cloud_recording_duration: int | None = None`
   - Update `rooms_join_meeting` handler:
     - Set `cloud_recording_available = bool(meeting.cloud_recording_s3_key)`
     - Set `cloud_recording_duration = meeting.cloud_recording_duration`

**Acceptance Criteria:**
- [ ] Schema includes `cloud_recording_available` field
- [ ] Schema includes `cloud_recording_duration` field
- [ ] Handler computes availability from S3 key presence
- [ ] Handler includes duration
- [ ] Type checking passes: `cd server && uv run mypy reflector/views/rooms.py`

**Files:** `server/reflector/views/rooms.py`

**References:** PRD lines 692-751

---

## Phase 6: Frontend Display

### Task 6.1: Display cloud recording player on transcript page

**Priority:** Medium (user-facing feature)

**Goal:** Show cloud recording audio player when available

**Changes:**
1. `www/app/(app)/transcripts/[transcriptId]/page.tsx`:
   - Add conditional section after existing audio player
   - Check `transcript.meeting?.cloud_recording_available`
   - Render audio element with src pointing to `/v1/meetings/${transcript.meeting_id}/cloud-recording`
   - Show duration if available (formatted as minutes:seconds)
   - Display warning about large file size (~38 MB/minute)
   - Add icon and labels ("Original Cloud Recording", "Brady Bunch grid layout")

**Acceptance Criteria:**
- [ ] Section only shows when `cloud_recording_available` is true
- [ ] Audio element src uses backend endpoint
- [ ] Duration displayed in human-readable format (e.g., "5m 23s")
- [ ] Warning text about large file size visible
- [ ] Descriptive text explains "Brady Bunch grid layout"
- [ ] Type checking passes: `cd www && pnpm tsc --noEmit`
- [ ] Styling consistent with existing audio player

**Files:** `www/app/(app)/transcripts/[transcriptId]/page.tsx`

**References:** PRD lines 753-799

---

## Phase 7: Manual Testing & Validation

### Task 7.1: End-to-end validation (single participant)

**Priority:** BLOCKER (must pass before deployment)

**Goal:** Validate full flow from meeting creation to cloud recording playback

**Test Procedure:**
1. Start services: `docker compose up -d postgres redis server worker`
2. Create test room via API (name: "dual-recording-test")
3. Create meeting
4. Join meeting from frontend
5. Verify browser console shows dual recording start
6. Verify server logs show raw-tracks start call
7. Speak for 20-30 seconds, leave meeting
8. Wait 2-5 minutes for Daily.co processing
9. Verify webhooks received (cloud + raw-tracks)
10. Check database for cloud_recording_s3_key and transcript status
11. Test cloud recording endpoint returns 307 redirect
12. Test frontend displays cloud recording player
13. Test audio playback works

**Acceptance Criteria:**
- [ ] Cloud recording webhook stores S3 key in meeting table
- [ ] Raw-tracks webhook triggers transcription pipeline
- [ ] Database query shows both cloud_recording_s3_key and transcript.title populated
- [ ] Cloud recording endpoint returns 307 with S3 presigned URL
- [ ] Frontend shows "Original Cloud Recording" section
- [ ] Audio player loads and plays cloud recording
- [ ] Processed transcript shows correct transcription (from raw-tracks)

**Test Artifacts:**
- Screenshot of browser console showing dual recording start
- Server log snippet showing webhook handling
- Database query results
- Screenshot of transcript page with cloud recording player

**References:** PRD lines 801-926

---

### Task 7.2: Multi-participant validation (idempotency test)

**Priority:** BLOCKER (determines if lock mechanism needed)

**Goal:** Validate Daily.co behavior with multiple participants starting recordings

**Test Procedure:**
1. Create new meeting
2. Open 2 browser windows (normal + incognito)
3. Join meeting from both windows nearly simultaneously (within 1 second)
4. Check browser consoles in both windows
5. Check server logs for 2x backend recording start calls
6. Check Daily.co dashboard for number of recordings created
7. Wait for webhooks
8. Analyze results

**Expected Outcomes:**
- **Best case:** Daily.co handles idempotency (1 cloud + 1 raw-tracks recording)
- **Acceptable:** Duplicate recordings but no errors
- **Bad:** Errors or corruption

**Acceptance Criteria:**
- [ ] Documented which outcome occurred
- [ ] If Best/Acceptable: proceed to deployment
- [ ] If Bad: implement Alternative Solution A or B from PRD
- [ ] Decision documented in DAILYCO_TEST.md

**Action Items Based on Results:**
- Best/Acceptable → Ship as-is
- Bad → Add Task 7.3 (Implement lock mechanism)

**References:** PRD lines 928-963

---

### Task 7.3: Implement lock mechanism (CONDITIONAL - only if Task 7.2 fails)

**Priority:** High (only if multi-participant test shows errors)

**Goal:** Prevent duplicate recording starts using database or Redis lock

**Two Options:**

**Option A: Database Lock**
- Add `recording_started: bool` field to Meeting model
- Add migration for new column
- Use database transaction to atomically check and set flag
- Return `is_first_participant` in join response
- Frontend only starts recordings if first participant

**Option B: Redis Lock**
- Use `RedisAsyncLock` from existing codebase
- Lock key: `meeting:{meeting_id}:recording-start`
- Check/set `meeting:{meeting_id}:recording-started` flag
- Return `is_first_participant` in join response
- Frontend only starts recordings if first participant

**Acceptance Criteria:**
- [ ] Multi-participant test (Task 7.2 rerun) shows only 1 recording created
- [ ] No race conditions under simultaneous joins
- [ ] Type checking passes
- [ ] Test with 3+ participants shows consistent behavior

**Files:**
- Option A: `server/reflector/db/meetings.py`, `server/reflector/views/rooms.py`, `www/app/[roomName]/components/DailyRoom.tsx`
- Option B: `server/reflector/views/rooms.py`, `www/app/[roomName]/components/DailyRoom.tsx`

**References:** PRD lines 966-1048

---

## Success Criteria (Overall Project)

### Functional Requirements
- [ ] Both cloud and raw-tracks recordings start when user joins meeting
- [ ] Cloud recording webhook stores S3 key in meeting table (DAILYCO_STORAGE bucket)
- [ ] Raw-tracks webhook triggers existing multitrack pipeline (unchanged)
- [ ] Cloud recording accessible via `/v1/meetings/{id}/cloud-recording` endpoint
- [ ] Transcript page displays cloud recording audio player when available
- [ ] Existing transcription quality unchanged (raw-tracks only)
- [ ] Dead code removed (JWT start_cloud_recording)

### Validation Requirements
- [ ] Prototype test (Task 0.1) confirms instanceId strategy
- [ ] Multi-participant test (Task 7.2) confirms Daily.co behavior documented
- [ ] End-to-end test (Task 7.1) shows both webhooks and data stored correctly
- [ ] Cloud recording playback works in frontend

### Non-Functional Requirements
- [ ] No performance degradation in webhook handling
- [ ] Database migration runs without errors
- [ ] Type checking passes (mypy, tsc)

---

## Dependencies

**Critical Path:**
```
Task 0.1 (instanceId validation)
  ↓
Task 0.2 + Task 0.3 (cleanup + frontend setup)
  ↓
Task 1.1 + Task 1.2 (database schema)
  ↓
Task 2.1 + Task 2.2 (API client)
  ↓
Task 3.1 (backend endpoint)
  ↓
Task 4.1 (webhook handler)
  ↓
Task 5.1 + Task 6.1 (API response + frontend display)
  ↓
Task 7.1 (E2E test)
  ↓
Task 7.2 (multi-participant test)
  ↓
[Task 7.3 if needed] (lock mechanism)
```

**Parallel Work Possible:**
- Tasks 1.1 + 1.2 can be done together (schema + models)
- Tasks 2.1 + 2.2 can be done together (API client layers)
- Tasks 5.1 + 6.1 can be done together (backend response + frontend display)

---

## Rollback Plan

**Immediate Mitigation (Production Issues):**
1. Revert frontend `DailyRoom.tsx` to remove dual recording start
2. This stops cloud recordings, raw-tracks continue normally

**Database Rollback:**
```bash
docker compose exec server uv run alembic downgrade -1
```

**Code Rollback:**
1. Revert frontend changes (Task 0.3, Task 6.1)
2. Revert webhook handler (Task 4.1) to only handle raw-tracks
3. Keep API endpoints (Task 3.1) - harmless if unused

---

## Storage Impact

**Current (raw-tracks only):** 80 MB/day = 2.4 GB/month = $0.06/month S3
**With cloud recording:** 11.5 GB/day = 345 GB/month = $7.94/month S3

**Recommendation:** Consider S3 lifecycle policy for cloud MP4s (delete after 90 days)

---

## Estimated Effort

**Phase 0:** 2-4 hours (prototype + cleanup)
**Phase 1:** 1 hour (database)
**Phase 2:** 1 hour (API client)
**Phase 3:** 2 hours (backend endpoint)
**Phase 4:** 2 hours (webhook handler)
**Phase 5:** 1 hour (meeting API)
**Phase 6:** 2 hours (frontend display)
**Phase 7:** 4 hours (testing)

**Total:** 15-17 hours base + 4 hours buffer = 19-21 hours (2-3 days)
