"""Integration test: ICS dedup against Max's real calendar feed.

Fetches the live ICS feed, picks an upcoming event, then simulates
a duplicate (different UID, same time window) to verify dedup logic.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from icalendar import Calendar

from reflector.db import get_database
from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.meetings import meetings
from reflector.db.rooms import rooms_controller
from reflector.services.ics_sync import ICSFetchService
from reflector.worker.ics_sync import create_upcoming_meetings_for_event

MAX_ICS_URL = (
    "https://user.fm/calendar/v1-929f6269635c3c3bebd57c32b23bf448/Max%20Calendar.ics"
)


def _find_upcoming_event(
    fetch_service: ICSFetchService, calendar: Calendar
) -> dict | None:
    """Find any upcoming event within next 48h (ignoring room matching)."""
    now = datetime.now(timezone.utc)
    window_end = now + timedelta(hours=48)

    for component in calendar.walk():
        if component.name != "VEVENT":
            continue
        status = component.get("STATUS", "").upper()
        if status == "CANCELLED":
            continue
        event_data = fetch_service._parse_event(component)
        if event_data and now < event_data["start_time"] < window_end:
            return event_data
    return None


@pytest.mark.asyncio
async def test_dedup_with_real_ics_feed():
    """Fetch Max's real ICS, pick an upcoming event, inject duplicate UID, verify dedup."""

    # 1. Fetch and parse real ICS feed
    fetch_service = ICSFetchService()
    ics_content = await fetch_service.fetch_ics(MAX_ICS_URL)
    calendar = fetch_service.parse_ics(ics_content)

    upcoming = _find_upcoming_event(fetch_service, calendar)
    if upcoming is None:
        pytest.skip("No upcoming events in Max's calendar within 48h window")

    # 2. Create a test room
    room = await rooms_controller.add(
        name="max-dedup-integration-test",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url=MAX_ICS_URL,
        ics_enabled=True,
    )

    start_time = upcoming["start_time"]
    end_time = upcoming["end_time"]
    title = upcoming["title"]

    # 3. Insert two calendar events with different UIDs but same time window
    event1 = await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid=upcoming["ics_uid"],  # real UID from the feed
            title=title,
            start_time=start_time,
            end_time=end_time,
        )
    )
    event2 = await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid=f"SYNTHETIC-DUPLICATE-{upcoming['ics_uid']}",
            title=title,
            start_time=start_time,
            end_time=end_time,
        )
    )

    create_window = datetime.now(timezone.utc) - timedelta(minutes=6)
    call_count = 0

    # 4. Mock the platform client, run both events through meeting creation
    with patch(
        "reflector.worker.ics_sync.create_platform_client"
    ) as mock_platform_factory:
        mock_client = AsyncMock()

        async def mock_create_meeting(room_name_prefix, *, end_date, room):
            nonlocal call_count
            call_count += 1
            return AsyncMock(
                meeting_id=f"integ-meeting-{call_count}",
                room_name=f"max-dedup-integration-test-{call_count}",
                room_url=f"https://mock.video/max-dedup-integration-test-{call_count}",
                host_room_url=f"https://mock.video/max-dedup-integration-test-{call_count}?host=true",
            )

        mock_client.create_meeting = mock_create_meeting
        mock_client.upload_logo = AsyncMock()
        mock_platform_factory.return_value = mock_client

        await create_upcoming_meetings_for_event(event1, create_window, room)
        await create_upcoming_meetings_for_event(event2, create_window, room)

    # 5. Verify: only 1 meeting created
    results = await get_database().fetch_all(
        meetings.select().where(meetings.c.room_id == room.id)
    )
    assert len(results) == 1, (
        f"Expected 1 meeting (dedup should block duplicate), got {len(results)}. "
        f"Event: {title} @ {start_time} - {end_time}"
    )
    assert call_count == 1, f"create_meeting called {call_count} times, expected 1"
