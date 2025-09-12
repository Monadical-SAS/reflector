# PR Feedback Work Items

## Security Issues

### 1. SSRF Vulnerability in ICS Fetch Service
**File:** `server/reflector/services/ics_sync.py:45-49`
**Issue:** The ICS fetch service doesn't validate or sanitize URLs before fetching them, which could lead to SSRF vulnerabilities.
**Severity:** ~~High~~ **Low** (Downgraded)
**Note:** After analysis, this is nearly unexploitable because:
- Runs async in Celery worker with 5+ minute delays
- No feedback to attacker (no errors, timing, or responses)
- Only processes valid ICS format
- Attacker can't verify if request succeeded or failed
**Decision:** Ignore for now - theoretical risk only

### 2. Race Condition in process_meetings
**File:** ~~`server/reflector/worker/ics_sync.py:149-219`~~ `server/reflector/worker/process.py:212-296`
**Issue:** Complex logic for handling meeting state transitions with potential race conditions when multiple workers process the same meeting simultaneously.
**Severity:** Medium
**Status:** ✅ FIXED - Implemented ExtendableLock with Redis
**Solution:** Added distributed locking using Redis with automatic lock extension for long-running processes:
- 60-second initial timeout with 30-second auto-extension
- Non-blocking acquisition to skip locked meetings
- Prevents duplicate processing across multiple workers

## Code Issues

### 3. Missing Import for meetings_controller
**File:** `server/reflector/views/rooms.py` (join meeting endpoint)
**Issue:** Missing import for `meetings_controller` will cause NameError.
**Severity:** High

### 4. Import Performance Issue
**File:** `server/reflector/views/rooms.py` (sync ICS endpoint)
**Issue:** `ics_sync_service` import is inside function body, imported on every request.
**Severity:** Low

### 5. Grace Period Logic Issue
**File:** `server/reflector/worker/ics_sync.py`
**Issue:** Grace period logic doesn't check if meeting is already inactive and doesn't verify if participants rejoined.
**Severity:** Medium

## Frontend Code Quality

### 6. Date Parameter Type Issue
**File:** `www/app/lib/timeUtils.ts:1`
**Issue:** Should just use "Date" and pass with `new Date(start_time)` - too much implicitness.
**Severity:** Low

### 7. Missing End Comment for Calendar Hooks
**File:** `www/app/lib/apiHooks.ts:749`
**Issue:** Need to signal end of "Calendar integration hooks" section.
**Severity:** Low

### 8. Non-null Assertion Issue
**File:** `www/app/lib/apiHooks.ts:650`
**Issue:** Using `roomName!` shadows null/undefined issues, better to fail explicitly.
**Severity:** Low

### 9. Missing Comment
**File:** `www/app/lib/apiHooks.ts:577`
**Issue:** Need comment like "Invalidate all meeting-related queries".
**Severity:** Low

### 10. Array Type Check
**File:** `www/app/lib/apiHooks.ts:582`
**Issue:** Should verify always returns array.
**Severity:** Low

### 11. Duplicate Condition Check
**File:** `www/app/lib/apiHooks.ts:584`
**Issue:** Should combine conditions: `&& (k.includes("/meetings/active") || k.includes("/meetings/upcoming"))`.
**Severity:** Low

### 12. Component Naming
**File:** `www/app/components/MinimalHeader.tsx:17`
**Issue:** Consider renaming to `MeetingMinimalHeader`.
**Severity:** Low

### 13. useEffect Meeting Creation Logic
**File:** `www/app/[roomName]/useRoomMeeting.tsx:46`
**Issue:** useEffect fires on any meetingId change, potentially creating duplicate meetings.
**Severity:** Medium

### 14. Obvious Comment
**File:** `www/app/[roomName]/page.tsx:374`
**Issue:** Comment seems obvious from code.
**Severity:** Low

### 15. URL Structure Concern
**File:** `www/app/[roomName]/page.tsx:302`
**Issue:** URL structure getting complex, needs refactoring.
**Severity:** Medium

### 16. Code Duplication (3rd time)
**File:** `www/app/[roomName]/[meetingId]/page.tsx:28`
**Issue:** Code repeated 3rd time, needs abstraction.
**Severity:** Medium

### 17. Copy-Paste Issue
**File:** `www/app/[roomName]/[meetingId]/page.tsx:43`
**Issue:** Code appears to be copy-pasted from `[roomName]/page.tsx`.
**Severity:** Medium

### 18. Unnecessary Code
**File:** `www/app/[roomName]/MeetingSelection.tsx:33`
**Issue:** Code not needed.
**Severity:** Low

### 19. Missing Punctuation
**File:** `www/app/[roomName]/MeetingSelection.tsx:57`
**Issue:** Missing period.
**Severity:** Low

### 20. Inconsistent Time Value
**File:** `www/app/[roomName]/MeetingSelection.tsx:73`
**Issue:** Comment says 1 or 5 minutes?
**Severity:** Low

### 21. Data Partitioning Logic
**File:** `www/app/[roomName]/MeetingSelection.tsx:76`
**Issue:** Extracting currentMeetings and upcomingMeetings may have intersection issues, needs partition function.
**Severity:** Medium

### 22. Missing Character
**File:** `www/app/[roomName]/MeetingSelection.tsx:104`
**Issue:** Missing "?".
**Severity:** Low

### 23. Code Duplication
**File:** `www/app/(app)/rooms/page.tsx:330`
**Issue:** Duplicates code after "detailedEditedRoom".
**Severity:** Medium

### 24. Emoji Constant
**File:** `www/app/(app)/rooms/page.tsx:835`
**Issue:** ✅ emoji should be a constant with string template.
**Severity:** Low

### 25. Missing Punctuation
**File:** `www/app/(app)/rooms/_components/ICSSettings.tsx:70`
**Issue:** Missing period.
**Severity:** Low

### 26. Type Safety Issue
**File:** `www/app/(app)/rooms/_components/RoomTable.tsx:87`
**Issue:** Use `meeting.calendar_metadata?.["title"]` instead of "as any".
**Severity:** Low

### 27. Duplicated Logic
**File:** `www/app/(app)/rooms/_components/RoomTable.tsx:114`
**Issue:** Minutes logic duplicated in another place.
**Severity:** Low

## Documentation

### 28. Unclear Purpose
**File:** `consent-handler.md`
**Issue:** What's this file for? Most likely NOT needed.
**Severity:** Low

## Error Handling

### 29. Silent Failures in pre_create_upcoming_meetings
**File:** `server/reflector/worker/ics_sync.py:103-198`
**Issue:** Function catches all exceptions at top level but doesn't properly handle individual meeting creation failures.
**Severity:** Medium

---

## Priority Levels:
- **High**: Items 1, 3
- **Medium**: Items 2, 5, 13, 15, 16, 17, 21, 23, 29
- **Low**: Items 4, 6, 7, 8, 9, 10, 11, 12, 14, 18, 19, 20, 22, 24, 25, 26, 27, 28
