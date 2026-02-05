# Batch Room Meeting Status Queries — Handoff Report

## Business Goal

The rooms list page (`/rooms`) fires **2N+2 HTTP requests** for N rooms. Each room card renders a `MeetingStatus` component that independently calls two hooks:

- `useRoomActiveMeetings(roomName)` → `GET /v1/rooms/{room_name}/meetings/active`
- `useRoomUpcomingMeetings(roomName)` → `GET /v1/rooms/{room_name}/meetings/upcoming`

Each of those endpoints internally does a room lookup by name (`LIMIT 1`) plus a data query. For 10 rooms, that's 22 HTTP requests and 20 DB queries on page load. This is a classic N+1 problem at the API layer.

**Goal: collapse all per-room meeting status queries into a single bulk POST request.**

## Approach: DataLoader-style Batching

We use [`@yornaath/batshit`](https://github.com/yornaath/batshit) — a lightweight DataLoader pattern for JS. It collects individual `.fetch(roomName)` calls within a 10ms window, deduplicates them, and dispatches one bulk request. Each caller gets back only their slice of the response.

This is **isomorphic**: removing the batcher and reverting the hooks to direct API calls would still work. The backend bulk endpoint is additive, the individual endpoints remain untouched.

## What Was Built

### Branch

`fix-room-query-batching` (worktree at `.worktrees/fix-room-query-batching/`)

### Backend Changes

**New bulk DB methods** (3 files):

| File | Method | Purpose |
|------|--------|---------|
| `server/reflector/db/rooms.py` | `RoomController.get_by_names(names)` | Fetch rooms by name list using `IN` clause |
| `server/reflector/db/meetings.py` | `MeetingController.get_all_active_for_rooms(room_ids, current_time)` | Active meetings for multiple rooms, one query |
| `server/reflector/db/calendar_events.py` | `CalendarEventController.get_upcoming_for_rooms(room_ids, minutes_ahead)` | Upcoming events for multiple rooms, one query |

**New endpoint** in `server/reflector/views/rooms.py`:

```
POST /v1/rooms/meetings/bulk-status
Body: { "room_names": ["room-a", "room-b", ...] }
Response: { "room-a": { "active_meetings": [...], "upcoming_events": [...] }, ... }
```

- 3 total DB queries regardless of room count (rooms lookup, active meetings, upcoming events)
- Auth masking applied: non-owners get `host_room_url=""` for Whereby, `description=null`/`attendees=null` for calendar events
- Registered before `/{room_id}` route to avoid path conflict
- Request/response models: `BulkStatusRequest`, `RoomMeetingStatus`

### Frontend Changes

**New dependency**: `@yornaath/batshit` (added to `www/package.json`)

**New file**: `www/app/lib/meetingStatusBatcher.ts`

```typescript
export const meetingStatusBatcher = create({
  fetcher: async (roomNames: string[]) => {
    const unique = [...new Set(roomNames)];
    const { data } = await client.POST("/v1/rooms/meetings/bulk-status", {
      body: { room_names: unique },
    });
    return roomNames.map((name) => ({
      roomName: name,
      active_meetings: data?.[name]?.active_meetings ?? [],
      upcoming_events: data?.[name]?.upcoming_events ?? [],
    }));
  },
  resolver: keyResolver("roomName"),
  scheduler: windowScheduler(10),  // 10ms batching window
});
```

**Modified hooks** in `www/app/lib/apiHooks.ts`:

- `useRoomActiveMeetings` — changed from `$api.useQuery("get", "/v1/rooms/{room_name}/meetings/active", ...)` to `useQuery` + `meetingStatusBatcher.fetch(roomName)`
- `useRoomUpcomingMeetings` — same pattern
- `useRoomsCreateMeeting` — cache invalidation updated from `$api.queryOptions(...)` to `meetingStatusKeys.active(roomName)`
- Added `meetingStatusKeys` query key factory: `{ active: (name) => ["rooms", name, "meetings/active"], upcoming: (name) => ["rooms", name, "meetings/upcoming"] }`

**Cache invalidation compatibility**: the new query keys contain `"meetings/active"` and `"meetings/upcoming"` as string elements, which the existing `useMeetingDeactivate` predicate matches via `.includes()`. No changes needed there.

**Regenerated**: `www/app/reflector-api.d.ts` from OpenAPI spec.

### Files Modified

| File | Change |
|------|--------|
| `server/reflector/db/rooms.py` | +`get_by_names()` |
| `server/reflector/db/meetings.py` | +`get_all_active_for_rooms()` |
| `server/reflector/db/calendar_events.py` | +`get_upcoming_for_rooms()` |
| `server/reflector/views/rooms.py` | +endpoint, +`BulkStatusRequest`, +`RoomMeetingStatus`, +imports (`asyncio`, `defaultdict`) |
| `www/package.json` | +`@yornaath/batshit` |
| `www/pnpm-lock.yaml` | Updated |
| `www/app/lib/meetingStatusBatcher.ts` | **New file** |
| `www/app/lib/apiHooks.ts` | Rewrote 2 hooks, added key factory, updated 1 invalidation |
| `www/app/reflector-api.d.ts` | Regenerated |

## Verification Status

**Tested:**
- Backend lint (ruff): clean
- Backend tests: 351 passed, 8 skipped (2 pre-existing flaky tests unrelated to this work: `test_transcript_rtc_and_websocket`, `test_transcript_upload_file`)
- TypeScript type check (`tsc --noEmit`): clean
- OpenAPI spec: bulk-status endpoint present and correctly typed
- Pre-commit hooks: all passed

**NOT tested (requires manual browser verification):**
- Open rooms list page → Network tab shows single `POST /v1/rooms/meetings/bulk-status` instead of 2N GETs
- Active meeting badges render correctly per room
- Upcoming meeting indicators render correctly per room
- Single room page (`MeetingSelection.tsx`) still works (batcher handles batch-of-1)
- Meeting deactivation → cache invalidates and meeting status refreshes
- Creating a meeting → active meetings badge updates

## Frontend Testing (Next Steps)

See `FRONTEND_TEST_RESEARCH.md` for a full research document on how to write unit tests for these hooks. Summary:

- **Approach**: `jest.mock()` on module-level `apiClient` and `meetingStatusBatcher`, `renderHook`/`waitFor` from `@testing-library/react`
- **Batcher testing**: unit test batcher directly with mock `client.POST`; test hooks with mock batcher module
- **New deps needed**: `@testing-library/react`, `@testing-library/jest-dom`, `@testing-library/dom`, `jest-environment-jsdom`
- **Key gotcha**: `openapi-react-query` reconstructed from mock client to test actual integration, or mock `$api` methods directly
- **Potential issues**: `ts-jest` v29 / Jest 30 compatibility, ESM handling for `openapi-react-query`

## How to Run

### Backend (Docker, from worktree)

```bash
cd .worktrees/fix-room-query-batching

# Symlink env files (not in git)
ln -sf /path/to/main/server/.env server/.env
ln -sf /path/to/main/www/.env.local www/.env.local
ln -sf /path/to/main/www/.env www/.env

# Start services
docker compose up -d redis postgres server
```

### Frontend (manual, per project convention)

```bash
cd .worktrees/fix-room-query-batching/www
pnpm install  # if not done
pnpm dev
```

### Backend Tests

```bash
cd .worktrees/fix-room-query-batching/server
REDIS_HOST=localhost CELERY_BROKER_URL=redis://localhost:6379/1 CELERY_RESULT_BACKEND=redis://localhost:6379/1 uv run pytest tests/ -q
```

### Regenerate OpenAPI Types

Requires the backend server running on port 1250:

```bash
cd .worktrees/fix-room-query-batching/server
REDIS_HOST=localhost CELERY_BROKER_URL=redis://localhost:6379/1 CELERY_RESULT_BACKEND=redis://localhost:6379/1 \
  uv run python -c "import json; from reflector.app import app; json.dump(app.openapi(), open('/tmp/openapi.json','w'))" 2>/dev/null

cd ../www
npx openapi-typescript /tmp/openapi.json -o ./app/reflector-api.d.ts
```
