"""
ICS Calendar Synchronization Service

This module provides services for fetching, parsing, and synchronizing ICS (iCalendar)
calendar feeds with room booking data in the database.

Key Components:
- ICSFetchService: Handles HTTP fetching and parsing of ICS calendar data
- ICSSyncService: Manages the synchronization process between ICS feeds and database

Example Usage:
    # Sync a room's calendar
    room = Room(id="room1", name="conference-room", ics_url="https://cal.example.com/room.ics")
    result = await ics_sync_service.sync_room_calendar(room)

    # Result structure:
    {
        "status": "success",  # success|unchanged|error|skipped
        "hash": "abc123...",  # MD5 hash of ICS content
        "events_found": 5,    # Events matching this room
        "total_events": 12,   # Total events in calendar within time window
        "events_created": 2,  # New events added to database
        "events_updated": 3,  # Existing events modified
        "events_deleted": 1   # Events soft-deleted (no longer in calendar)
    }

Event Matching:
    Events are matched to rooms by checking if the room's full URL appears in the
    event's LOCATION or DESCRIPTION fields. Only events within a 25-hour window
    (1 hour ago to 24 hours from now) are processed.

Input: ICS calendar URL (e.g., "https://calendar.google.com/calendar/ical/...")
Output: EventData objects with structured calendar information:
    {
        "ics_uid": "event123@google.com",
        "title": "Team Meeting",
        "description": "Weekly sync meeting",
        "location": "https://meet.company.com/conference-room",
        "start_time": datetime(2024, 1, 15, 14, 0, tzinfo=UTC),
        "end_time": datetime(2024, 1, 15, 15, 0, tzinfo=UTC),
        "attendees": [
            {"email": "user@company.com", "name": "John Doe", "role": "ORGANIZER"},
            {"email": "attendee@company.com", "name": "Jane Smith", "status": "ACCEPTED"}
        ],
        "ics_raw_data": "BEGIN:VEVENT\nUID:event123@google.com\n..."
    }
"""

import hashlib
from datetime import date, datetime, timedelta, timezone
from enum import Enum
from typing import TypedDict

import httpx
import pytz
import structlog
from icalendar import Calendar, Event

from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.rooms import Room, rooms_controller
from reflector.settings import settings

logger = structlog.get_logger()

EVENT_WINDOW_DELTA_START = timedelta(hours=-1)
EVENT_WINDOW_DELTA_END = timedelta(hours=24)


class SyncStatus(str, Enum):
    SUCCESS = "success"
    UNCHANGED = "unchanged"
    ERROR = "error"
    SKIPPED = "skipped"


class AttendeeData(TypedDict, total=False):
    email: str | None
    name: str | None
    status: str | None
    role: str | None


class EventData(TypedDict):
    ics_uid: str
    title: str | None
    description: str | None
    location: str | None
    start_time: datetime
    end_time: datetime
    attendees: list[AttendeeData]
    ics_raw_data: str


class SyncStats(TypedDict):
    events_created: int
    events_updated: int
    events_deleted: int


class SyncResultBase(TypedDict):
    status: SyncStatus


class SyncResult(SyncResultBase, total=False):
    hash: str | None
    events_found: int
    total_events: int
    events_created: int
    events_updated: int
    events_deleted: int
    error: str | None
    reason: str | None


class ICSFetchService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0, headers={"User-Agent": "Reflector/1.0"}
        )

    async def fetch_ics(self, url: str) -> str:
        response = await self.client.get(url)
        response.raise_for_status()

        return response.text

    def parse_ics(self, ics_content: str) -> Calendar:
        return Calendar.from_ical(ics_content)

    def extract_room_events(
        self, calendar: Calendar, room_name: str, room_url: str
    ) -> tuple[list[EventData], int]:
        events = []
        total_events = 0
        now = datetime.now(timezone.utc)
        window_start = now + timedelta(hours=EVENT_WINDOW_DELTA_START)
        window_end = now + timedelta(hours=EVENT_WINDOW_DELTA_END)

        for component in calendar.walk():
            if component.name != "VEVENT":
                continue

            status = component.get("STATUS", "").upper()
            if status == "CANCELLED":
                continue

            # Count total non-cancelled events in the time window
            event_data = self._parse_event(component)
            if event_data and window_start <= event_data["start_time"] <= window_end:
                total_events += 1

                # Check if event matches this room
                if self._event_matches_room(component, room_name, room_url):
                    events.append(event_data)

        return events, total_events

    def _event_matches_room(self, event: Event, room_name: str, room_url: str) -> bool:
        location = str(event.get("LOCATION", ""))
        description = str(event.get("DESCRIPTION", ""))

        # Only match full room URL
        # XXX leaved here as a patterns, to later be extended with tinyurl or such too
        patterns = [
            room_url,
        ]

        # Check location and description for patterns
        text_to_check = f"{location} {description}".lower()
        for pattern in patterns:
            if pattern.lower() in text_to_check:
                return True

        return False

    def _parse_event(self, event: Event) -> EventData | None:
        uid = str(event.get("UID", ""))
        summary = str(event.get("SUMMARY", ""))
        description = str(event.get("DESCRIPTION", ""))
        location = str(event.get("LOCATION", ""))
        dtstart = event.get("DTSTART")
        dtend = event.get("DTEND")

        if not dtstart:
            return None

        # Convert fields
        start_time = self._normalize_datetime(
            dtstart.dt if hasattr(dtstart, "dt") else dtstart
        )
        end_time = (
            self._normalize_datetime(dtend.dt if hasattr(dtend, "dt") else dtend)
            if dtend
            else start_time + timedelta(hours=1)
        )
        attendees = self._parse_attendees(event)

        # Get raw event data for storage
        raw_data = event.to_ical().decode("utf-8")

        return {
            "ics_uid": uid,
            "title": summary,
            "description": description,
            "location": location,
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
            "ics_raw_data": raw_data,
        }

    def _normalize_datetime(self, dt) -> datetime:
        # Ensure datetime is with timezone, if not, assume UTC
        if isinstance(dt, date) and not isinstance(dt, datetime):
            dt = datetime.combine(dt, datetime.min.time())
            dt = pytz.UTC.localize(dt)
        elif isinstance(dt, datetime):
            if dt.tzinfo is None:
                dt = pytz.UTC.localize(dt)
            else:
                dt = dt.astimezone(pytz.UTC)

        return dt

    def _parse_attendees(self, event: Event) -> list[AttendeeData]:
        # Extracts attendee information from both ATTENDEE and ORGANIZER properties.
        # Handles malformed comma-separated email addresses in single ATTENDEE fields
        # by splitting them into separate attendee entries. Returns a list of attendee
        # data including email, name, status, and role information.
        final_attendees = []

        attendees = event.get("ATTENDEE", [])
        if not isinstance(attendees, list):
            attendees = [attendees]
        for att in attendees:
            email_str = str(att).replace("mailto:", "") if att else None

            # Handle malformed comma-separated email addresses in a single ATTENDEE field
            if email_str and "," in email_str:
                # Split comma-separated emails and create separate attendee entries
                email_parts = [email.strip() for email in email_str.split(",")]
                for email in email_parts:
                    if email and "@" in email:
                        clean_email = email.replace("MAILTO:", "").replace(
                            "mailto:", ""
                        )
                        att_data: AttendeeData = {
                            "email": clean_email,
                            "name": att.params.get("CN")
                            if hasattr(att, "params") and email == email_parts[0]
                            else None,
                            "status": att.params.get("PARTSTAT")
                            if hasattr(att, "params") and email == email_parts[0]
                            else None,
                            "role": att.params.get("ROLE")
                            if hasattr(att, "params") and email == email_parts[0]
                            else None,
                        }
                        final_attendees.append(att_data)
            else:
                # Normal single attendee
                att_data: AttendeeData = {
                    "email": email_str,
                    "name": att.params.get("CN") if hasattr(att, "params") else None,
                    "status": att.params.get("PARTSTAT")
                    if hasattr(att, "params")
                    else None,
                    "role": att.params.get("ROLE") if hasattr(att, "params") else None,
                }
                final_attendees.append(att_data)

        # Add organizer
        organizer = event.get("ORGANIZER")
        if organizer:
            org_email = (
                str(organizer).replace("mailto:", "").replace("MAILTO:", "")
                if organizer
                else None
            )
            org_data: AttendeeData = {
                "email": org_email,
                "name": organizer.params.get("CN")
                if hasattr(organizer, "params")
                else None,
                "role": "ORGANIZER",
            }
            final_attendees.append(org_data)

        return final_attendees


class ICSSyncService:
    def __init__(self):
        self.fetch_service = ICSFetchService()

    async def sync_room_calendar(self, room: Room) -> SyncResult:
        if not room.ics_enabled or not room.ics_url:
            return {"status": SyncStatus.SKIPPED, "reason": "ICS not configured"}

        try:
            if not self._should_sync(room):
                return {"status": SyncStatus.SKIPPED, "reason": "Not time to sync yet"}

            ics_content = await self.fetch_service.fetch_ics(room.ics_url)
            calendar = self.fetch_service.parse_ics(ics_content)

            content_hash = hashlib.md5(ics_content.encode()).hexdigest()
            if room.ics_last_etag == content_hash:
                logger.info("No changes in ICS for room", room_id=room.id)
                room_url = f"{settings.UI_BASE_URL}/{room.name}"
                events, total_events = self.fetch_service.extract_room_events(
                    calendar, room.name, room_url
                )
                return {
                    "status": SyncStatus.UNCHANGED,
                    "hash": content_hash,
                    "events_found": len(events),
                    "total_events": total_events,
                    "events_created": 0,
                    "events_updated": 0,
                    "events_deleted": 0,
                }

            # Extract matching events
            room_url = f"{settings.UI_BASE_URL}/{room.name}"
            events, total_events = self.fetch_service.extract_room_events(
                calendar, room.name, room_url
            )
            sync_result = await self._sync_events_to_database(room.id, events)

            # Update room sync metadata
            await rooms_controller.update(
                room,
                {
                    "ics_last_sync": datetime.now(timezone.utc),
                    "ics_last_etag": content_hash,
                },
                mutate=False,
            )

            return {
                "status": SyncStatus.SUCCESS,
                "hash": content_hash,
                "events_found": len(events),
                "total_events": total_events,
                **sync_result,
            }

        except Exception as e:
            logger.error("Failed to sync ICS for room", room_id=room.id, error=str(e))
            return {"status": SyncStatus.ERROR, "error": str(e)}

    def _should_sync(self, room: Room) -> bool:
        if not room.ics_last_sync:
            return True

        time_since_sync = datetime.now(timezone.utc) - room.ics_last_sync
        return time_since_sync.total_seconds() >= room.ics_fetch_interval

    async def _sync_events_to_database(
        self, room_id: str, events: list[EventData]
    ) -> SyncStats:
        created = 0
        updated = 0

        current_ics_uids = []

        for event_data in events:
            calendar_event = CalendarEvent(room_id=room_id, **event_data)
            existing = await calendar_events_controller.get_by_ics_uid(
                room_id, event_data["ics_uid"]
            )

            if existing:
                updated += 1
            else:
                created += 1

            await calendar_events_controller.upsert(calendar_event)
            current_ics_uids.append(event_data["ics_uid"])

        # Soft delete events that are no longer in calendar
        deleted = await calendar_events_controller.soft_delete_missing(
            room_id, current_ics_uids
        )

        return {
            "events_created": created,
            "events_updated": updated,
            "events_deleted": deleted,
        }


ics_sync_service = ICSSyncService()
