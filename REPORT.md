# Fix: Daily.co UX & ICS Meeting Dedup

Branch: `fix-daily-ux` (worktree at `.worktrees/fix-daily-ux`)
Base: `main` (`1ce1c7a9`)

## Context / Incident

Feb 2, ~11:30 AM Montreal — user JLee reported being "kicked out / can't rejoin" Max's room. Screenshot showed "Failed to join meeting. try again." Two active meetings were visible with ~1s creation difference, plus one recently deactivated.

### Root Cause Analysis

**The kick**: Exact cause unknown (server logs lost — container recreated ~Feb 3). `eject_at_room_exp` is NOT set on Daily rooms (defaults false), so room expiry did NOT eject users. Most likely a WebRTC connection drop or Daily.co infrastructure hiccup. After disconnection, rejoin failed because the meeting had passed `end_date` → join endpoint returned 400 "Meeting has ended" → frontend showed generic error.

**The duplicate meetings**: Max's room uses an aggregated ICS feed (user.fm) that merges Cal.com + Google Calendar. Every Cal.com booking appears twice with different `ics_uid` values — one `@Cal.com`, one UUID from Google Calendar. Reflector deduplicates by `ics_uid`, so it creates 2 `calendar_event` rows → 2 meetings → 2 Daily rooms. This is systematic and ongoing for every Cal.com booking. Proven with production DB data across Feb 2, 3, 5.

## What's Done

### Commit 1: `e9e16764` — Daily.co error messages
**File**: `www/app/[roomName]/components/DailyRoom.tsx`

- Added `frame.on("error", handler)` for Daily.co `DailyEventObjectFatalError` events
- `fatalError` state + ref to distinguish forced disconnect from voluntary leave
- Specific error screens per `error.type`:
  - `connection-error` → "Connection lost" + "Try Rejoining" (page reload) + "Leave"
  - `exp-room` → "Meeting time has ended" + "Back to Room"
  - `ejected` → "You were removed" + "Back to Room"
  - fallback → shows `errorMsg` + "Back to Room"
- Join failure (`joinMutation.isError`) now shows actual API error detail via `printApiError` instead of generic message
- Added "Back to Room" button on join failure screen

### Commit 2: `1da687fe` — ICS meeting dedup
**Files**: `server/reflector/db/meetings.py`, `server/reflector/worker/ics_sync.py`, `server/tests/test_ics_dedup.py`

- `MeetingController.get_by_room_and_time_window(room, start_date, end_date)` — queries for existing active meeting with exact same room + start + end times
- In `create_upcoming_meetings_for_event`: after checking `get_by_calendar_event`, also checks `get_by_room_and_time_window`. If a meeting already exists for the same time slot, skips creation and logs it.
- 2 tests: dedup prevents duplicate, different times still create separate meetings. Both pass.

### Commit 3: `238d7684` — Review fixes
- Import `ApiError` type instead of inline type literal in cast
- Move `get_database` import from inline to top-of-file in test

## What's Left / Known Issues

### Must fix: `joinMutation.error as ApiError` cast
In `DailyRoom.tsx:404`, the `as ApiError` cast is needed because `openapi-react-query` types the error based on the OpenAPI spec (which declares `detail: ValidationError[]` for all errors), but real 400 errors return `{ detail: "string" }`. This is a known codebase-wide issue (see `apiHooks.ts:12` XXX comment). The cast is safe at runtime (`printApiError` handles both string and array), but it's a type-level lie. Proper fix: either fix the OpenAPI error response schemas, or make `printApiError` accept `unknown` and do full runtime narrowing. Both are broader changes beyond this PR's scope.

### Not tested (needs manual verification)
- Daily.co error event rendering — requires live Daily room in browser to trigger `error` events. Cannot be tested locally without a running meeting.
- The "Try Rejoining" button simply reloads the page. Could be improved to re-call the join endpoint directly without full reload.

### Layer A (ICS feed config) not addressed
The dedup code fix (Layer B) prevents duplicate meetings, but the root cause is Max's aggregated calendar feed including both Cal.com and Google Calendar copies. Configuring the ICS URL to point directly at Cal.com's feed (or deduplicating at the feed level) would eliminate the duplicate `calendar_event` rows too. This is a user configuration change, not a code change.

### Dedup edge case: shared rooms
The dedup check uses exact `(room_id, start_date, end_date)` match. For shared rooms where multiple people could legitimately book the same time slot, this could incorrectly skip a valid meeting. Currently not an issue since Max's room is personal, but worth noting if this logic is applied broadly. Could add a guard like `if not room.is_shared` if needed.

### No DB index for dedup query
`get_by_room_and_time_window` queries on `(room_id, start_date, end_date, is_active)`. Existing `idx_meeting_room_id` index on `room_id` is sufficient for current scale. No composite index added.

## Files Changed (total: +315/-4)
```
www/app/[roomName]/components/DailyRoom.tsx  — +93 (error event handling, error UIs)
server/reflector/db/meetings.py              — +21 (get_by_room_and_time_window)
server/reflector/worker/ics_sync.py          — +17/-2 (dedup check before meeting creation)
server/tests/test_ics_dedup.py               — +186 (new test file, 2 tests)
```
