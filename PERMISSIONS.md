## Permissions

This document describes permissions for authenticated vs anonymous users across frontend pages and backend API endpoints. Some behavior is controlled by feature flags. See Environment toggles (backend) and Feature flags (frontend) for global auth and gating controls.

### Glossary

- Anonymous user: request without a valid Bearer token.
- Authenticated user: request with a valid Bearer token.
- Owner: the user whose `sub` matches `resource.user_id`.
- Shared room: room with `is_shared=true`.
- Transcript share modes:
  - private: owner-only
  - semi-private: any authenticated user
  - public: anyone
  - anonymous transcript: `user_id is null`; readable by anyone (share mode not enforced)

### Frontend pages (Next.js)

- Home `/`:

  - Automatically redirects to `/transcripts/new`

- Transcripts

  - `/transcripts/new`: requires login when `requireLogin` is true; otherwise public. Create UI/action is shown when authenticated.
  - `/transcripts/[transcriptId]`: requires login when `requireLogin` is true; otherwise accessible based on transcript share mode.
  - `/transcripts/[transcriptId]/record`: requires login when `requireLogin` is true.
  - `/transcripts/[transcriptId]/upload`: requires login when `requireLogin` is true.
  - `/transcripts/[transcriptId]/correct`: requires login when `requireLogin` is true.

- Browse `/browse`:

  - Feature-gated by `FEATURE_BROWSE`. If disabled, redirects to home.
  - Requires login when `requireLogin` is true.

- Rooms `/rooms`:

  - Feature-gated by `FEATURE_ROOMS`. If disabled, redirects to home.
  - Requires login when `requireLogin` is true.

- Room by name `/[roomName]`:

  - Public. Intended for joining a meeting; no forced auth.

- About/Privacy `(aboutAndPrivacy)/about`, `(aboutAndPrivacy)/privacy`:

  - Public.

- Webinars `/webinars/[title]`:

  - Public.

### Backend API endpoints (FastAPI)

General auth pattern:

- Most endpoints accept an optional user (`current_user_optional`) and enforce visibility via controllers.
- List/search endpoints require auth when configured (see Environment toggles / `PUBLIC_MODE`).

Endpoints:

- `GET /v1/transcripts` — list transcripts

  - Auth: Requires auth when `PUBLIC_MODE` is false; otherwise anonymous allowed.
  - Scope: With auth returns own items + items in shared rooms; anonymous returns only items in shared rooms.

- `GET /v1/transcripts/search` — full-text search

  - Auth: Requires auth when `PUBLIC_MODE` is false; otherwise anonymous allowed.
  - Scope: Same as list.

- `POST /v1/transcripts` — create transcript

  - Auth: Anonymous allowed; created transcript is anonymous (`user_id = null`) unless a token is provided.

- `GET /v1/transcripts/{id}` — fetch transcript

  - Auth: Anonymous allowed, but access is enforced by transcript visibility:
    - If `user_id is null`: public to anyone.
    - If `share_mode = public`: public to anyone.
    - If `share_mode = semi-private`: any authenticated user can access.
    - If `share_mode = private`: only owner can access.

- `PATCH /v1/transcripts/{id}` — update transcript

  - Auth: Anonymous allowed. Any caller who can READ the transcript per share mode can UPDATE it (owner for private; any authenticated user for semi-private; anyone for public or anonymous transcripts). No explicit owner check on update.

- `DELETE /v1/transcripts/{id}` — delete transcript

  - Auth: No explicit auth required. Deletion proceeds unless an authenticated non-owner is detected; anonymous callers and non-owner callers without a token can delete. If the transcript belongs to a meeting in a shared room, the handler explicitly bypasses the owner check. (Known risk.)

- `GET /v1/transcripts/{id}/topics` | `GET /with-words` | `GET /topics/{topicId}/words-per-speaker`

  - Auth: Anonymous allowed; access follows `get_by_id_for_http` rules above.

- `POST /v1/transcripts/{id}/zulip`

  - Auth: Anonymous allowed but requires access to transcript; also feature `sendToZulip` is used on frontend. Backend will send via configured Zulip credentials.

- `GET /v1/transcripts/{id}/audio/mp3` (and `HEAD`)

  - Auth: Anonymous allowed. If transcript has `user_id`, a signed short-lived `token` query param can grant access for non-authenticated downloads; otherwise requires user access via `get_by_id_for_http` (through `user_id` from token if present).
  - Storage proxying is handled; 404 when deleted or missing.

- `GET /v1/transcripts/{id}/audio/waveform`

  - Auth: Anonymous allowed; transcript access rules apply.

- `POST /v1/transcripts/{id}/record/webrtc`

  - Auth: Anonymous allowed if transcript accessible and not locked.

- `POST /v1/transcripts/{id}/record/upload`

  - Auth: Anonymous allowed if transcript accessible and not locked.

- `POST /v1/transcripts/{id}/process`

  - Auth: Anonymous allowed if transcript accessible and in correct state; schedules processing.

- Participants and Speakers

  - `GET/POST /v1/transcripts/{id}/participants` and `GET/PATCH/DELETE /v1/transcripts/{id}/participants/{participant_id}`
  - `PATCH /v1/transcripts/{id}/speaker/assign` and `PATCH /v1/transcripts/{id}/speaker/merge`
  - Auth: Anonymous allowed; access controlled by `get_by_id_for_http`. Any caller who can READ the transcript per share mode can MODIFY participants/speakers (owner for private; any authenticated user for semi-private; anyone for public/anonymous transcripts). No explicit owner check on these mutations.

- WebSocket events

  - `GET /v1/transcripts/{id}/events` — placeholder
  - `WS /v1/transcripts/{id}/events` — no auth; accepts if transcript exists; does NOT enforce share mode visibility (anyone with the ID can subscribe).

- Rooms

  - `GET /v1/rooms` — list rooms
    - Auth: Requires auth when `PUBLIC_MODE` is false; otherwise anonymous allowed.
    - Scope: With auth returns own + shared; anonymous returns shared only.
  - `GET /v1/rooms/{room_id}` — fetch room
    - Auth: Anonymous allowed; no ownership restriction on read, but only shared rooms are visible via listings; direct fetch returns 404 if not found.
  - `POST /v1/rooms` — create room
    - Auth: Anonymous allowed; room is associated to `user_id` if token provided, otherwise created with `user_id = null` is not supported by schema (requires `user_id`): in practice this endpoint expects an authenticated user; without token `user_id` becomes `None` which likely fails downstream. Intended: authenticated only.
  - `PATCH /v1/rooms/{room_id}` — update room
    - Auth: Anonymous allowed; no ownership check is enforced. Any caller can update a room (known risk).
  - `DELETE /v1/rooms/{room_id}` — delete room
    - Auth: Anonymous allowed; only owner can delete.
  - `POST /v1/rooms/{room_name}/meeting` — create or fetch active meeting
    - Auth: Anonymous allowed; if requester is not owner, response omits host URL (`host_room_url = ""`).
  - `POST /v1/rooms/{room_id}/webhook/test` — test webhook
    - Auth: Anonymous allowed; owner allowed; non-owner authenticated users receive 403 (anonymous bypasses the owner check).

- Meetings

  - `POST /v1/meetings/{meeting_id}/consent`
    - Auth: Anonymous allowed; records consent with optional `user_id` if provided.

- Whereby webhook `POST /v1/whereby` (no prefix check in code, included under `/v1` via router)

  - Auth: No Bearer auth; requires valid `whereby-signature` header and recent timestamp.

- Zulip

  - `GET /v1/zulip/streams` and `GET /v1/zulip/streams/{id}/topics`
    - Auth: Requires authenticated user (explicit 403 if missing).

- User
  - `GET /v1/me` — returns current user info or `null` if anonymous.

### Frontend pages → API endpoints

- Home `/`:

  - Redirects to `/transcripts/new` (no direct API call)

- Transcripts

  - `/transcripts/new`:

    - `POST /v1/transcripts`

  - `/transcripts/{transcript_id}`:

    - `GET /v1/transcripts/{transcript_id}`
    - `GET /v1/transcripts/{transcript_id}/topics`
    - `GET /v1/transcripts/{transcript_id}/audio/waveform`
    - `GET /v1/transcripts/{transcript_id}/audio/mp3`
    - `PATCH /v1/transcripts/{transcript_id}`
    - Zulip helpers:
      - `GET /v1/zulip/streams`
      - `GET /v1/zulip/streams/{stream_id}/topics`
      - `POST /v1/transcripts/{transcript_id}/zulip`

  - `/transcripts/{transcript_id}/record`:

    - `GET /v1/transcripts/{transcript_id}`
    - `POST /v1/transcripts/{transcript_id}/record/webrtc`
    - `WS /v1/transcripts/{transcript_id}/events`

  - `/transcripts/{transcript_id}/upload`:

    - `GET /v1/transcripts/{transcript_id}`
    - `POST /v1/transcripts/{transcript_id}/record/upload`

  - `/transcripts/{transcript_id}/correct`:
    - `GET /v1/transcripts/{transcript_id}`
    - `PATCH /v1/transcripts/{transcript_id}`
    - `GET /v1/transcripts/{transcript_id}/topics/{topic_id}/words-per-speaker`
    - Participants:
      - `GET /v1/transcripts/{transcript_id}/participants`
      - `POST /v1/transcripts/{transcript_id}/participants`
      - `PATCH /v1/transcripts/{transcript_id}/participants/{participant_id}`
      - `DELETE /v1/transcripts/{transcript_id}/participants/{participant_id}`
    - Speakers:
      - `PATCH /v1/transcripts/{transcript_id}/speaker/assign`
      - `PATCH /v1/transcripts/{transcript_id}/speaker/merge`

- Browse `/browse`:

  - `GET /v1/transcripts/search` (supports `q`, `limit`, `offset`, `room_id`, `source_kind`)
  - `DELETE /v1/transcripts/{transcript_id}`
  - `POST /v1/transcripts/{transcript_id}/process`
  - `GET /v1/rooms`

- Rooms `/rooms`:

  - `GET /v1/rooms`
  - `GET /v1/rooms/{room_id}`
  - `POST /v1/rooms`
  - `PATCH /v1/rooms/{room_id}`
  - `DELETE /v1/rooms/{room_id}`
  - `POST /v1/rooms/{room_id}/webhook/test`
  - Zulip helpers:
    - `GET /v1/zulip/streams`
    - `GET /v1/zulip/streams/{stream_id}/topics`

- Room by name `/[roomName]`:

  - `POST /v1/rooms/{room_name}/meeting`
  - `POST /v1/meetings/{meeting_id}/consent`

- Webinars `/webinars/{title}`:

  - `POST /v1/rooms/{room_name}/meeting`
  - External registration: Google Forms `POST` (no backend API)

- About & Privacy `(aboutAndPrivacy)/about`, `(aboutAndPrivacy)/privacy`:

  - Public content; no backend API

### Feature flags (frontend)

- `requireLogin` (`FEATURE_REQUIRE_LOGIN`): if true, middleware enforces auth on `/`, `/transcripts(.*)`, `/browse(.*)`, `/rooms(.*)`.
- `browse` (`FEATURE_BROWSE`): controls access to `/browse`; disabled → redirect to home.
- `rooms` (`FEATURE_ROOMS`): controls access to `/rooms`; disabled → redirect to home.
- `sendToZulip` (`FEATURE_SEND_TO_ZULIP`): UI feature; backend endpoints remain available but UI may hide actions.
- `privacy` (`FEATURE_PRIVACY`): UI-only display feature.

### Environment toggles (backend)

- `AUTH_BACKEND` = `none` (default) or `jwt`: when `none`, all requests are effectively anonymous; when `jwt`, Bearer tokens populate `user`.
- `PUBLIC_MODE` (default false): if false, transcript and room listing/search require authentication; if true, anonymous users can list shared rooms/transcripts.

### Summary of current behavior

- Anonymous users:

  - Can access public pages (About, Privacy, Webinars, Room join by name) and, if `requireLogin` is false, can access home and transcripts UI; otherwise redirected to login.
  - Backend: Can read items according to visibility (anonymous transcripts, public transcripts, items in shared rooms). Can modify only resources they are authorized to via `get_by_id_for_http` (e.g., anonymous transcripts they created or items in shared rooms when allowed by share mode). Cannot use Zulip streams/topics endpoints; can post a transcript to Zulip when the transcript is accessible.

- Authenticated users:
  - Full UI access per feature flags; can create transcripts, manage their rooms, view their transcripts plus those in shared rooms.
  - Can access semi-private transcripts and their own private ones; cannot access others' private transcripts.

### Inconsistencies to discuss and align (UI vs API)

1. UI protects pages broadly; API often allows anonymous

   - UI middleware requires auth for `/`, `/transcripts(.*)`, `/browse(.*)`, `/rooms(.*)` when `requireLogin=true`.
   - API endpoints for these sections largely accept anonymous access and rely on controller checks.
   - Decision: Either loosen UI gating when `PUBLIC_MODE=true` or tighten API to require auth consistently for modifying operations and protected reads when `requireLogin=true`.

2. Transcripts list/search enablement

   - UI: `useTranscriptsSearch` is enabled unconditionally (no auth check) in `www/app/lib/apiHooks.ts`.
   - API: `GET /v1/transcripts` and `/v1/transcripts/search` require auth when `PUBLIC_MODE=false`.
   - Impact: With `requireLogin=true` and `PUBLIC_MODE=false`, UI might still attempt calls pre-auth; will receive 401.
   - Options: Gate UI queries behind `useAuthReady().isAuthenticated` when `requireLogin=true`; or allow anonymous list/search only when `PUBLIC_MODE=true`.

3. Rooms list/get enablement

   - UI: `useRoomsList` and `useRoomGet` are enabled only when authenticated.
   - API: Allows anonymous to list shared rooms and fetch rooms even when `PUBLIC_MODE=true`; and returns 401 for list when `PUBLIC_MODE=false`.
   - Decision: If `PUBLIC_MODE=true`, consider enabling rooms list/get for anonymous in UI; otherwise tighten API.

4. Transcript details/topics enablement vs API

   - UI: `useTranscriptGet` and `useTranscriptTopics` do not require auth by default; `useTranscriptWaveform` also does not. `useTranscriptMP3` is enabled only when authenticated.
   - API: Allows anonymous access but enforces `share_mode` and `user_id`. This is consistent. No action needed unless we decide to require auth when `requireLogin=true`.

5. Transcript topics with words and per speaker

   - UI: `useTranscriptTopicsWithWords` and `useTranscriptTopicsWithWordsPerSpeaker` are enabled only when authenticated.
   - API: Endpoints allow anonymous when transcript is accessible.
   - Decision: Either remove UI auth gating for these reads (for consistent anonymous viewing of public/semi-private), or require auth on API.

6. Participants endpoints

   - UI: Reads and mutations (create/update/delete) require auth in hooks.
   - API: Allows anonymous if transcript is accessible; permission enforced via `get_by_id_for_http` but anonymous could potentially mutate anonymous/shared transcripts.
   - Decision: Require auth on API for mutation endpoints, or allow anonymous in UI accordingly (likely prefer requiring auth to modify participants).

7. Speaker assign/merge

   - UI: Mutations require auth.
   - API: Allows anonymous if transcript accessible.
   - Decision: Align by requiring auth for these mutation endpoints.

8. Transcript create

   - UI: Creation is available; not explicitly gated by auth in `useTranscriptCreate`.
   - API: Allows anonymous create (creates anonymous transcript). This is consistent with a public mode but may conflict with `requireLogin=true` UX.
   - Decision: If `requireLogin=true`, either gate the UI button/action behind auth or return 401 from API when `requireLogin=true`.

9. Rooms create/update/delete

   - UI: Mutations require auth (hooks enabled behind auth via list pages and forms).
   - API: Accepts anonymous and relies on `user_id` for ownership; however, `rooms.add` requires a non-null `user_id` (schema requires), so anonymous likely fails at DB layer if reached.
   - Decision: Explicitly require auth at API for these endpoints to avoid ambiguous behavior.

10. Rooms create meeting `/rooms/{room_name}/meeting`

- UI: Called from public room page `/[roomName]` with no auth requirement.
- API: Allows anonymous; if requester is not owner, host URL is removed — this is intentional.
- Status: Consistent by design.

11. Zulip endpoints

- UI: Streams/topics hooks enabled only when authenticated; post-to-zulip mutation available when feature enabled.
- API: Explicitly requires authenticated user for streams/topics; post-to-zulip checks transcript access only.
- Decision: Consider requiring auth for `/transcripts/{id}/zulip` as well (UI expects an authenticated user context to pick streams/topics).

12. WebSocket events

- UI: Public use of websocket to `/v1/transcripts/{id}/events`.
- API: No auth; validates transcript exists.
- Status: Consistent with public viewing of accessible transcripts; revisit if `requireLogin=true` implies gating.

13. Feature flags vs backend toggles

- UI `requireLogin` can force login while API still permits anonymous unless `PUBLIC_MODE=false` and endpoint checks 401. This leads to 401s surfaced in UI pre-auth for certain queries.
- Decision: Introduce a backend setting mirroring `requireLogin` or set UI behavior based on `PUBLIC_MODE` to determine whether to enable anonymous calls.

Proposed alignment strategy (to decide before implementation):

- Reads: Allow anonymous only when `PUBLIC_MODE=true`; otherwise require auth and gate UI queries accordingly.
- Mutations (create/update/delete/assign/merge/participants): Require auth across the board, both UI and API.
- Special cases: Keep meeting creation anonymous for `/[roomName]` flow with host URL stripping.

### Security risks identified

- Transcript delete may allow non-owners to delete

  - In `DELETE /v1/transcripts/{id}` the handler resets `user_id=None` when the transcript belongs to a shared room, which bypasses the owner check in the controller. This allows anonymous or non-owner users to delete transcripts in shared rooms if they know the ID.

- Participants and speakers mutations are not owner-restricted

  - `POST/PATCH/DELETE /v1/transcripts/{id}/participants` and `PATCH /v1/transcripts/{id}/speaker/*` rely only on `get_by_id_for_http`. For semi-private transcripts, any authenticated user can read and therefore mutate; no explicit owner check is enforced.

- Rooms mutations accept anonymous (confusing/unsafe)

  - `POST/PATCH/DELETE /v1/rooms` use optional auth. Create with no token passes `user_id=None` into `rooms_controller.add` where `user_id` is required by schema; this can lead to unexpected failures. Update/delete silently no-op if not owner rather than returning 401/403. Behavior is ambiguous and weakens posture.

- Room read-by-id exposes non-shared rooms by ID

  - `GET /v1/rooms/{room_id}` does not restrict access based on ownership or sharing. Anyone who guesses a room ID can fetch its metadata. If this is not desired, it is a data exposure risk.

- Zulip post endpoint allows anonymous posting

  - `POST /v1/transcripts/{id}/zulip` does not require authentication and only checks transcript access. This could permit anonymous users to trigger messages via our Zulip bot for public/semi-private transcripts.

- WebSocket events do not enforce transcript visibility

  - `WS /v1/transcripts/{id}/events` only checks that the transcript exists (`get_by_id`), not access rules (`get_by_id_for_http`). Anyone with an ID can subscribe to events for private transcripts.

- UI/API gating mismatch

  - With `requireLogin=true` and `PUBLIC_MODE=false`, the UI still triggers some queries (e.g., search) before auth, causing avoidable 401s and making assumptions that differ from the backend’s anonymous access policy.

### Action plan to improve security

- Tighten authorization on all mutation endpoints (owner-only)

  - Require authenticated user (`current_user`) and enforce `transcript.user_id == user_id` for:
    - `PATCH /v1/transcripts/{id}`
    - `DELETE /v1/transcripts/{id}` (exception: allow when `transcript.user_id is None` and treat anonymous transcript as ownerless)
    - `POST/PATCH/DELETE /v1/transcripts/{id}/participants`
    - `PATCH /v1/transcripts/{id}/speaker/assign` and `/merge`

- Restrict semi-private transcript writes to owner-only

  - Semi-private should widen READ scope only; for WRITE operations (transcript PATCH, participants CRUD, speaker assign/merge, process/upload/webrtc), enforce owner-only checks consistently across handlers.

- Align transcript creation with `requireLogin`

  - When `requireLogin=true`, return 401 for unauthenticated `POST /v1/transcripts` (backend) and gate/hide create in the UI. This avoids anonymous creates when the UI requires login.

- Fix transcript delete logic for shared rooms

  - Remove the code path that sets `user_id=None` for transcripts in shared rooms. Deletion should remain owner-only (or ownerless only), regardless of room sharing.

- Require authentication for rooms mutations

  - Switch `POST/PATCH/DELETE /v1/rooms` to use `current_user` (not optional). Return 401 if missing; 403 if non-owner.

- Reassess room read-by-id exposure

  - Option A: Enforce visibility on `GET /v1/rooms/{room_id}`: allow owner or `is_shared=true`; otherwise 403.
  - Option B: Keep current behavior but explicitly document that direct fetch by ID is public metadata.

- Require authentication for Zulip post

  - Make `POST /v1/transcripts/{id}/zulip` require `current_user`; consider enforcing owner-only to prevent cross-account spam.

- Enforce transcript visibility on WebSocket

  - Switch websocket to use `get_by_id_for_http` with optional user: deny access to private transcripts for non-owners; allow semi-private to authenticated users; allow public/anonymous only when permitted by share mode.

- Align UI gating with backend policy

  - Gate `useTranscriptsSearch` (and similar reads) behind authentication when `requireLogin=true` and/or when `PUBLIC_MODE=false`.
  - Optionally add a backend flag (e.g., `REQUIRE_LOGIN`) mirroring the UI `requireLogin` to centralize policy. The UI can fetch `/v1/me` and feature flags to decide which queries to enable.

- Add audit/logging and tests

  - Log 401/403 decisions on sensitive endpoints and record `transcript_id/room_id` and caller `sub`.
  - Add tests for: non-owner delete denied, non-owner participant/speaker mutations denied, websocket access enforced by share mode, rooms mutations require auth.
