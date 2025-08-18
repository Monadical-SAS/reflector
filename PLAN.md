# ICS Calendar Integration Plan

## Core Concept
ICS calendar URLs are attached to rooms (not users) to enable automatic meeting tracking and management through periodic fetching of calendar data.

## Database Schema Updates

### 1. Add ICS configuration to rooms
- Add `ics_url` field to room table (URL to .ics file, may include auth token)
- Add `ics_fetch_interval` field to room table (default: 5 minutes, configurable)
- Add `ics_enabled` boolean field to room table
- Add `ics_last_sync` timestamp field to room table

### 2. Create calendar_events table
- `id` - UUID primary key
- `room_id` - Foreign key to room
- `external_id` - ICS event UID
- `title` - Event title
- `description` - Event description
- `start_time` - Event start timestamp
- `end_time` - Event end timestamp
- `attendees` - JSON field with attendee list and status
- `location` - Meeting location (should contain room name)
- `last_synced` - Last sync timestamp
- `is_deleted` - Boolean flag for soft delete (preserve past events)
- `ics_raw_data` - TEXT field to store raw VEVENT data for reference

### 3. Update meeting table
- Add `calendar_event_id` - Foreign key to calendar_events
- Add `calendar_metadata` - JSON field for additional calendar data
- Remove unique constraint on room_id + active status (allow multiple active meetings per room)

## Backend Implementation

### 1. ICS Sync Service
- Create background task that runs based on room's `ics_fetch_interval` (default: 5 minutes)
- For each room with ICS enabled, fetch the .ics file via HTTP/HTTPS
- Parse ICS file using icalendar library
- Extract VEVENT components and filter events looking for room URL (e.g., "https://reflector.monadical.com/max")
- Store matching events in calendar_events table
- Mark events as "upcoming" if start_time is within next 30 minutes
- Pre-create Whereby meetings 1 minute before start (ensures no delay when users join)
- Soft-delete future events that were removed from calendar (set is_deleted=true)
- Never delete past events (preserve for historical record)
- Support authenticated ICS feeds via tokens embedded in URL

### 2. Meeting Management Updates
- Allow multiple active meetings per room
- Pre-create meeting record 1 minute before calendar event starts (ensures meeting is ready)
- Link meeting to calendar_event for metadata
- Keep meeting active for 15 minutes after last participant leaves (grace period)
- Don't auto-close if new participant joins within grace period

### 3. API Endpoints
- `GET /v1/rooms/{room_name}/meetings` - List all active and upcoming meetings for a room
  - Returns filtered data based on user role (owner vs participant)
- `GET /v1/rooms/{room_name}/meetings/upcoming` - List upcoming meetings (next 30 min)
  - Returns filtered data based on user role
- `POST /v1/rooms/{room_name}/meetings/{meeting_id}/join` - Join specific meeting
- `PATCH /v1/rooms/{room_id}` - Update room settings (including ICS configuration)
  - ICS fields only visible/editable by room owner
- `POST /v1/rooms/{room_name}/ics/sync` - Trigger manual ICS sync
  - Only accessible by room owner
- `GET /v1/rooms/{room_name}/ics/status` - Get ICS sync status and last fetch time
  - Only accessible by room owner

## Frontend Implementation

### 1. Room Settings Page
- Add ICS configuration section
- Field for ICS URL (e.g., Google Calendar private URL, Outlook ICS export)
- Field for fetch interval (dropdown: 1 min, 5 min, 10 min, 30 min, 1 hour)
- Test connection button (validates ICS file can be fetched and parsed)
- Manual sync button
- Show last sync time and next scheduled sync

### 2. Meeting Selection Page (New)
- Show when accessing `/room/{room_name}`
- **Host view** (room owner):
  - Full calendar event details
  - Meeting title and description
  - Complete attendee list with RSVP status
  - Number of current participants
  - Duration (how long it's been running)
- **Participant view** (non-owners):
  - Meeting title only
  - Date and time
  - Number of current participants
  - Duration (how long it's been running)
  - No attendee list or description (privacy)
- Display upcoming meetings (visible 30min before):
  - Show countdown to start
  - Can click to join early → redirected to waiting page
  - Waiting page shows countdown until meeting starts
  - Meeting pre-created by background task (ready when users arrive)
- Option to create unscheduled meeting (uses existing flow)

### 3. Meeting Room Updates
- Show calendar metadata in meeting info
- Display invited attendees vs actual participants
- Show meeting title from calendar event

## Meeting Lifecycle

### 1. Meeting Creation
- Automatic: Pre-created 1 minute before calendar event starts (ensures Whereby room is ready)
- Manual: User creates unscheduled meeting (existing `/rooms/{room_name}/meeting` endpoint)
- Background task handles pre-creation to avoid delays when users join

### 2. Meeting Join Rules
- Can join active meetings immediately
- Can see upcoming meetings 30 minutes before start
- Can click to join upcoming meetings early → sent to waiting page
- Waiting page automatically transitions to meeting at scheduled time
- Unscheduled meetings always joinable (current behavior)

### 3. Meeting Closure Rules
- All meetings: 15-minute grace period after last participant leaves
- If participant rejoins within grace period, keep meeting active
- Calendar meetings: Force close 30 minutes after scheduled end time
- Unscheduled meetings: Keep active for 8 hours (current behavior)

## ICS Parsing Logic

### 1. Event Matching
- Parse ICS file using Python icalendar library
- Iterate through VEVENT components
- Check LOCATION field for full FQDN URL (e.g., "https://reflector.monadical.com/max")
- Check DESCRIPTION for room URL or mention
- Support multiple formats:
  - Full URL: "https://reflector.monadical.com/max"
  - With /room path: "https://reflector.monadical.com/room/max"
  - Partial paths: "room/max", "/max room"

### 2. Attendee Extraction
- Parse ATTENDEE properties from VEVENT
- Extract email (MAILTO), name (CN parameter), and RSVP status (PARTSTAT)
- Store as JSON in calendar_events.attendees

### 3. Sync Strategy
- Fetch complete ICS file (contains all events)
- Filter events from (now - 1 hour) to (now + 24 hours) for processing
- Update existing events if LAST-MODIFIED or SEQUENCE changed
- Delete future events that no longer exist in ICS (start_time > now)
- Keep past events for historical record (never delete if start_time < now)
- Handle recurring events (RRULE) - expand to individual instances
- Track deleted calendar events to clean up future meetings
- Cache ICS file hash to detect changes and skip unnecessary processing

## Security Considerations

### 1. ICS URL Security
- ICS URLs may contain authentication tokens (e.g., Google Calendar private URLs)
- Store full ICS URLs encrypted using Fernet to protect embedded tokens
- Validate ICS URLs (must be HTTPS for production)
- Never expose full ICS URLs in API responses (return masked version)
- Rate limit ICS fetching to prevent abuse

### 2. Room Access
- Only room owner can configure ICS URL
- ICS URL shown as masked version to room owner (hides embedded tokens)
- ICS settings not visible to other users
- Meeting list visible to all room participants
- ICS fetch logs only visible to room owner

### 3. Meeting Privacy
- Full calendar details visible only to room owner
- Participants see limited info: title, date/time only
- Attendee list and description hidden from non-owners
- Meeting titles visible in room listing to all

## Implementation Phases

### Phase 1: Database and ICS Setup (Week 1) ✅ COMPLETED (2025-08-18)
1. ✅ Created database migrations for ICS fields and calendar_events table
   - Added ics_url, ics_fetch_interval, ics_enabled, ics_last_sync, ics_last_etag to room table
   - Created calendar_event table with ics_uid (instead of external_id) and proper typing
   - Added calendar_event_id and calendar_metadata (JSONB) to meeting table
   - Removed server_default from datetime fields for consistency
2. ✅ Installed icalendar Python library for ICS parsing
   - Added icalendar>=6.0.0 to dependencies
   - No encryption needed - ICS URLs are read-only
3. ✅ Built ICS fetch and sync service
   - Simple HTTP fetching without unnecessary validation
   - Proper TypedDict typing for event data structures
   - Supports any standard ICS format
4. ⚠️ API endpoints for ICS configuration (partial)
   - Room model updated to support ICS fields via existing PATCH endpoint
   - Dedicated ICS endpoints still pending
5. ⚠️ Celery background tasks for periodic sync (pending)
6. ✅ Tests written and passing
   - 6 tests for Room ICS fields
   - 7 tests for CalendarEvent model
   - All 13 tests passing

### Phase 2: Meeting Management (Week 2)
1. Update meeting lifecycle logic
2. Support multiple active meetings
3. Implement grace period logic
4. Link meetings to calendar events

### Phase 3: Frontend Meeting Selection (Week 3)
1. Build meeting selection page
2. Show active and upcoming meetings
3. Implement waiting page for early joiners
4. Add automatic transition from waiting to meeting
5. Support unscheduled meeting creation

### Phase 4: Calendar Integration UI (Week 4)
1. Add ICS settings to room configuration
2. Display calendar metadata in meetings
3. Show attendee information
4. Add sync status indicators
5. Show fetch interval and next sync time

## Success Metrics
- Zero merged meetings from consecutive calendar events
- Successful ICS sync from major providers (Google Calendar, Outlook, Apple Calendar, Nextcloud)
- Meeting join accuracy: correct meeting 100% of the time
- Grace period prevents 90% of accidental meeting closures
- Configurable fetch intervals reduce unnecessary API calls

## Design Decisions
1. **ICS attached to room, not user** - Prevents duplicate meetings from multiple calendars
2. **Multiple active meetings per room** - Supported with meeting selection page
3. **Grace period for rejoining** - 15 minutes after last participant leaves
4. **Upcoming meeting visibility** - Show 30 minutes before, join only on time
5. **Calendar data storage** - Attached to meeting record for full context
6. **No "ad-hoc" meetings** - Use existing meeting creation flow (unscheduled meetings)
7. **ICS configuration via room PATCH** - Reuse existing room configuration endpoint
8. **Event deletion handling** - Soft-delete future events, preserve past meetings
9. **Configurable fetch interval** - Balance between freshness and server load
10. **ICS over CalDAV** - Simpler implementation, wider compatibility, no complex auth

## Phase 1 Implementation Files Created

### Database Models
- `/server/reflector/db/rooms.py` - Updated with ICS fields (url, fetch_interval, enabled, last_sync, etag)
- `/server/reflector/db/calendar_events.py` - New CalendarEvent model with ics_uid and proper typing
- `/server/reflector/db/meetings.py` - Updated with calendar_event_id and calendar_metadata (JSONB)

### Services
- `/server/reflector/services/ics_sync.py` - ICS fetching with TypedDict for proper typing

### Tests
- `/server/tests/test_room_ics.py` - Room model ICS fields tests (6 tests)
- `/server/tests/test_calendar_event.py` - CalendarEvent model tests (7 tests)

### Key Design Decisions
- No encryption needed - ICS URLs are read-only access
- Using ics_uid instead of external_id for clarity
- Proper TypedDict typing for event data structures
- Removed unnecessary URL validation and webcal handling
- calendar_metadata in meetings stores flexible calendar data (organizer, recurrence, etc)

## Implementation Approach

### ICS Fetching vs CalDAV
- **ICS Benefits**:
  - Simpler implementation (HTTP GET vs CalDAV protocol)
  - Wider compatibility (all calendar apps can export ICS)
  - No authentication complexity (simple URL with optional token)
  - Easier debugging (ICS is plain text)
  - Lower server requirements (no CalDAV library dependencies)

### Supported Calendar Providers
1. **Google Calendar**: Private ICS URL from calendar settings
2. **Outlook/Office 365**: ICS export URL from calendar sharing
3. **Apple Calendar**: Published calendar ICS URL
4. **Nextcloud**: Public/private calendar ICS export
5. **Any CalDAV server**: Via ICS export endpoint

### ICS URL Examples
- Google: `https://calendar.google.com/calendar/ical/{calendar_id}/private-{token}/basic.ics`
- Outlook: `https://outlook.live.com/owa/calendar/{id}/calendar.ics`
- Custom: `https://example.com/calendars/room-schedule.ics`

### Fetch Interval Configuration
- 1 minute: For critical/high-activity rooms
- 5 minutes (default): Balance of freshness and efficiency
- 10 minutes: Standard meeting rooms
- 30 minutes: Low-activity rooms
- 1 hour: Rarely-used rooms or stable schedules