# ICS Calendar Integration - Implementation Guide

## Overview
This document provides detailed implementation guidance for integrating ICS calendar feeds with Reflector rooms. Unlike CalDAV which requires complex authentication and protocol handling, ICS integration uses simple HTTP(S) fetching of calendar files.

## Key Differences from CalDAV Approach

| Aspect | CalDAV | ICS |
|--------|--------|-----|
| Protocol | WebDAV extension | HTTP/HTTPS GET |
| Authentication | Username/password, OAuth | Tokens embedded in URL |
| Data Access | Selective event queries | Full calendar download |
| Implementation | Complex (caldav library) | Simple (requests + icalendar) |
| Real-time Updates | Supported | Polling only |
| Write Access | Yes | No (read-only) |

## Technical Architecture

### 1. ICS Fetching Service

```python
# reflector/services/ics_sync.py

import requests
from icalendar import Calendar
from typing import List, Optional
from datetime import datetime, timedelta

class ICSFetchService:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Reflector/1.0'})

    def fetch_ics(self, url: str) -> str:
        """Fetch ICS file from URL (authentication via URL token if needed)."""
        response = self.session.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    def parse_ics(self, ics_content: str) -> Calendar:
        """Parse ICS content into calendar object."""
        return Calendar.from_ical(ics_content)

    def extract_room_events(self, calendar: Calendar, room_url: str) -> List[dict]:
        """Extract events that match the room URL."""
        events = []

        for component in calendar.walk():
            if component.name == "VEVENT":
                # Check if event matches this room
                if self._event_matches_room(component, room_url):
                    events.append(self._parse_event(component))

        return events

    def _event_matches_room(self, event, room_url: str) -> bool:
        """Check if event location or description contains room URL."""
        location = str(event.get('LOCATION', ''))
        description = str(event.get('DESCRIPTION', ''))

        # Support various URL formats
        patterns = [
            room_url,
            room_url.replace('https://', ''),
            room_url.split('/')[-1],  # Just room name
        ]

        for pattern in patterns:
            if pattern in location or pattern in description:
                return True

        return False
```

### 2. Database Schema

```sql
-- Modify room table
ALTER TABLE room ADD COLUMN ics_url TEXT;  -- encrypted to protect embedded tokens
ALTER TABLE room ADD COLUMN ics_fetch_interval INTEGER DEFAULT 300;  -- seconds
ALTER TABLE room ADD COLUMN ics_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE room ADD COLUMN ics_last_sync TIMESTAMP;
ALTER TABLE room ADD COLUMN ics_last_etag TEXT;  -- for caching

-- Calendar events table
CREATE TABLE calendar_event (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    room_id UUID REFERENCES room(id) ON DELETE CASCADE,
    external_id TEXT NOT NULL,  -- ICS UID
    title TEXT,
    description TEXT,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    attendees JSONB,
    location TEXT,
    ics_raw_data TEXT,  -- Store raw VEVENT for reference
    last_synced TIMESTAMP DEFAULT NOW(),
    is_deleted BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(room_id, external_id)
);

-- Index for efficient queries
CREATE INDEX idx_calendar_event_room_start ON calendar_event(room_id, start_time);
CREATE INDEX idx_calendar_event_deleted ON calendar_event(is_deleted) WHERE NOT is_deleted;
```

### 3. Background Tasks

```python
# reflector/worker/tasks/ics_sync.py

from celery import shared_task
from datetime import datetime, timedelta
import hashlib

@shared_task
def sync_ics_calendars():
    """Sync all enabled ICS calendars based on their fetch intervals."""
    rooms = Room.query.filter_by(ics_enabled=True).all()

    for room in rooms:
        # Check if it's time to sync based on fetch interval
        if should_sync(room):
            sync_room_calendar.delay(room.id)

@shared_task
def sync_room_calendar(room_id: str):
    """Sync calendar for a specific room."""
    room = Room.query.get(room_id)
    if not room or not room.ics_enabled:
        return

    try:
        # Fetch ICS file (decrypt URL first)
        service = ICSFetchService()
        decrypted_url = decrypt_ics_url(room.ics_url)
        ics_content = service.fetch_ics(decrypted_url)

        # Check if content changed (using ETag or hash)
        content_hash = hashlib.md5(ics_content.encode()).hexdigest()
        if room.ics_last_etag == content_hash:
            logger.info(f"No changes in ICS for room {room_id}")
            return

        # Parse and extract events
        calendar = service.parse_ics(ics_content)
        events = service.extract_room_events(calendar, room.url)

        # Update database
        sync_events_to_database(room_id, events)

        # Update sync metadata
        room.ics_last_sync = datetime.utcnow()
        room.ics_last_etag = content_hash
        db.session.commit()

    except Exception as e:
        logger.error(f"Failed to sync ICS for room {room_id}: {e}")

def should_sync(room) -> bool:
    """Check if room calendar should be synced."""
    if not room.ics_last_sync:
        return True

    time_since_sync = datetime.utcnow() - room.ics_last_sync
    return time_since_sync.total_seconds() >= room.ics_fetch_interval
```

### 4. Celery Beat Schedule

```python
# reflector/worker/celeryconfig.py

from celery.schedules import crontab

beat_schedule = {
    'sync-ics-calendars': {
        'task': 'reflector.worker.tasks.ics_sync.sync_ics_calendars',
        'schedule': 60.0,  # Check every minute which calendars need syncing
    },
    'pre-create-meetings': {
        'task': 'reflector.worker.tasks.ics_sync.pre_create_calendar_meetings',
        'schedule': 60.0,  # Check every minute for upcoming meetings
    },
}
```

## API Endpoints

### Room ICS Configuration

```python
# PATCH /v1/rooms/{room_id}
{
    "ics_url": "https://calendar.google.com/calendar/ical/.../private-token/basic.ics",
    "ics_fetch_interval": 300,  # seconds
    "ics_enabled": true
    # URL will be encrypted in database to protect embedded tokens
}
```

### Manual Sync Trigger

```python
# POST /v1/rooms/{room_name}/ics/sync
# Response:
{
    "status": "syncing",
    "last_sync": "2024-01-15T10:30:00Z",
    "events_found": 5
}
```

### ICS Status

```python
# GET /v1/rooms/{room_name}/ics/status
# Response:
{
    "enabled": true,
    "last_sync": "2024-01-15T10:30:00Z",
    "next_sync": "2024-01-15T10:35:00Z",
    "fetch_interval": 300,
    "events_count": 12,
    "upcoming_events": 3
}
```

## ICS Parsing Details

### Event Field Mapping

| ICS Field | Database Field | Notes |
|-----------|---------------|-------|
| UID | external_id | Unique identifier |
| SUMMARY | title | Event title |
| DESCRIPTION | description | Full description |
| DTSTART | start_time | Convert to UTC |
| DTEND | end_time | Convert to UTC |
| LOCATION | location | Check for room URL |
| ATTENDEE | attendees | Parse into JSON |
| ORGANIZER | attendees | Add as organizer |
| STATUS | (internal) | Filter cancelled events |

### Handling Recurring Events

```python
def expand_recurring_events(event, start_date, end_date):
    """Expand recurring events into individual occurrences."""
    from dateutil.rrule import rrulestr

    if 'RRULE' not in event:
        return [event]

    # Parse recurrence rule
    rrule_str = event['RRULE'].to_ical().decode()
    dtstart = event['DTSTART'].dt

    # Generate occurrences
    rrule = rrulestr(rrule_str, dtstart=dtstart)
    occurrences = []

    for dt in rrule.between(start_date, end_date):
        # Clone event with new date
        occurrence = event.copy()
        occurrence['DTSTART'].dt = dt
        if 'DTEND' in event:
            duration = event['DTEND'].dt - event['DTSTART'].dt
            occurrence['DTEND'].dt = dt + duration

        # Unique ID for each occurrence
        occurrence['UID'] = f"{event['UID']}_{dt.isoformat()}"
        occurrences.append(occurrence)

    return occurrences
```

### Timezone Handling

```python
def normalize_datetime(dt):
    """Convert various datetime formats to UTC."""
    import pytz
    from datetime import datetime

    if hasattr(dt, 'dt'):  # icalendar property
        dt = dt.dt

    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            # Assume local timezone if naive
            dt = pytz.timezone('UTC').localize(dt)
        else:
            # Convert to UTC
            dt = dt.astimezone(pytz.UTC)

    return dt
```

## Security Considerations

### 1. URL Validation

```python
def validate_ics_url(url: str) -> bool:
    """Validate ICS URL for security."""
    from urllib.parse import urlparse

    parsed = urlparse(url)

    # Must be HTTPS in production
    if not settings.DEBUG and parsed.scheme != 'https':
        return False

    # Prevent local file access
    if parsed.scheme in ('file', 'ftp'):
        return False

    # Prevent internal network access
    if is_internal_ip(parsed.hostname):
        return False

    return True
```

### 2. Rate Limiting

```python
# Implement per-room rate limiting
RATE_LIMITS = {
    'min_fetch_interval': 60,  # Minimum 1 minute between fetches
    'max_requests_per_hour': 60,  # Max 60 requests per hour per room
    'max_file_size': 10 * 1024 * 1024,  # Max 10MB ICS file
}
```

### 3. ICS URL Encryption

```python
from cryptography.fernet import Fernet

class URLEncryption:
    def __init__(self):
        self.cipher = Fernet(settings.ENCRYPTION_KEY)

    def encrypt_url(self, url: str) -> str:
        """Encrypt ICS URL to protect embedded tokens."""
        return self.cipher.encrypt(url.encode()).decode()

    def decrypt_url(self, encrypted: str) -> str:
        """Decrypt ICS URL for fetching."""
        return self.cipher.decrypt(encrypted.encode()).decode()

    def mask_url(self, url: str) -> str:
        """Mask sensitive parts of URL for display."""
        from urllib.parse import urlparse, urlunparse

        parsed = urlparse(url)
        # Keep scheme, host, and path structure but mask tokens
        if '/private-' in parsed.path:
            # Google Calendar format
            parts = parsed.path.split('/private-')
            masked_path = parts[0] + '/private-***' + parts[1].split('/')[-1]
        elif 'token=' in url:
            # Query parameter token
            masked_path = parsed.path
            parsed = parsed._replace(query='token=***')
        else:
            # Generic masking of path segments that look like tokens
            import re
            masked_path = re.sub(r'/[a-zA-Z0-9]{20,}/', '/***/', parsed.path)

        return urlunparse(parsed._replace(path=masked_path))
```

## Testing Strategy

### 1. Unit Tests

```python
# tests/test_ics_sync.py

def test_ics_parsing():
    """Test ICS file parsing."""
    ics_content = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-123
SUMMARY:Team Meeting
LOCATION:https://reflector.monadical.com/engineering
DTSTART:20240115T100000Z
DTEND:20240115T110000Z
END:VEVENT
END:VCALENDAR"""

    service = ICSFetchService()
    calendar = service.parse_ics(ics_content)
    events = service.extract_room_events(
        calendar,
        "https://reflector.monadical.com/engineering"
    )

    assert len(events) == 1
    assert events[0]['title'] == 'Team Meeting'
```

### 2. Integration Tests

```python
def test_full_sync_flow():
    """Test complete sync workflow."""
    # Create room with ICS URL (encrypt URL to protect tokens)
    encryption = URLEncryption()
    room = Room(
        name="test-room",
        ics_url=encryption.encrypt_url("https://example.com/calendar.ics?token=secret"),
        ics_enabled=True
    )

    # Mock ICS fetch
    with patch('requests.get') as mock_get:
        mock_get.return_value.text = sample_ics_content

        # Run sync
        sync_room_calendar(room.id)

        # Verify events created
        events = CalendarEvent.query.filter_by(room_id=room.id).all()
        assert len(events) > 0
```

## Common ICS Provider Configurations

### Google Calendar
- URL Format: `https://calendar.google.com/calendar/ical/{calendar_id}/private-{token}/basic.ics`
- Authentication via token embedded in URL
- Updates every 3-8 hours by default

### Outlook/Office 365
- URL Format: `https://outlook.office365.com/owa/calendar/{id}/calendar.ics`
- May include token in URL path or query parameters
- Real-time updates

### Apple iCloud
- URL Format: `webcal://p{XX}-caldav.icloud.com/published/2/{token}`
- Convert webcal:// to https://
- Token embedded in URL path
- Public calendars only

### Nextcloud/ownCloud
- URL Format: `https://cloud.example.com/remote.php/dav/public-calendars/{token}`
- Token embedded in URL path
- Configurable update frequency

## Migration from CalDAV

If migrating from an existing CalDAV implementation:

1. **Database Migration**: Rename fields from `caldav_*` to `ics_*`
2. **URL Conversion**: Most CalDAV servers provide ICS export endpoints
3. **Authentication**: Convert from username/password to URL-embedded tokens
4. **Remove Dependencies**: Uninstall caldav library, add icalendar
5. **Update Background Tasks**: Replace CalDAV sync with ICS fetch

## Performance Optimizations

1. **Caching**: Use ETag/Last-Modified headers to avoid refetching unchanged calendars
2. **Incremental Sync**: Store last sync timestamp, only process new/modified events
3. **Batch Processing**: Process multiple room calendars in parallel
4. **Connection Pooling**: Reuse HTTP connections for multiple requests
5. **Compression**: Support gzip encoding for large ICS files

## Monitoring and Debugging

### Metrics to Track
- Sync success/failure rate per room
- Average sync duration
- ICS file sizes
- Number of events processed
- Failed event matches

### Debug Logging
```python
logger.debug(f"Fetching ICS from {room.ics_url}")
logger.debug(f"ICS content size: {len(ics_content)} bytes")
logger.debug(f"Found {len(events)} matching events")
logger.debug(f"Event UIDs: {[e['external_id'] for e in events]}")
```

### Common Issues
1. **SSL Certificate Errors**: Add certificate validation options
2. **Timeout Issues**: Increase timeout for large calendars
3. **Encoding Problems**: Handle various character encodings
4. **Timezone Mismatches**: Always convert to UTC
5. **Memory Issues**: Stream large ICS files instead of loading entirely