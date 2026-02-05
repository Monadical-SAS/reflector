from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db import get_database
from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.meetings import meetings
from reflector.db.rooms import rooms_controller
from reflector.worker.ics_sync import create_upcoming_meetings_for_event


@pytest.mark.asyncio
async def test_duplicate_calendar_event_does_not_create_duplicate_meeting():
    """When an aggregated ICS feed contains the same event with different UIDs
    (e.g. Cal.com UID + Google Calendar UUID), only one meeting should be created."""

    room = await rooms_controller.add(
        name="dedup-test-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/dedup.ics",
        ics_enabled=True,
    )

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(hours=1)
    end_time = now + timedelta(hours=2)

    # Create first calendar event (Cal.com UID)
    event1 = await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid="abc123@Cal.com",
            title="Team Standup",
            start_time=start_time,
            end_time=end_time,
        )
    )

    # create_window must be before start_time for the function to proceed
    create_window = now - timedelta(minutes=6)

    # Create meeting for event1
    with patch(
        "reflector.worker.ics_sync.create_platform_client"
    ) as mock_platform_factory:
        mock_client = AsyncMock()
        mock_client.create_meeting.return_value = AsyncMock(
            meeting_id="meeting-1",
            room_name="dedup-test-room-abc",
            room_url="https://mock.video/dedup-test-room-abc",
            host_room_url="https://mock.video/dedup-test-room-abc?host=true",
        )
        mock_client.upload_logo = AsyncMock()
        mock_platform_factory.return_value = mock_client

        await create_upcoming_meetings_for_event(event1, create_window, room)

    # Verify meeting was created
    results = await get_database().fetch_all(
        meetings.select().where(meetings.c.room_id == room.id)
    )
    assert len(results) == 1, f"Expected 1 meeting, got {len(results)}"

    # Create second calendar event with different UID but same time window (Google Calendar UUID)
    event2 = await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid="550e8400-e29b-41d4-a716-446655440000",
            title="Team Standup",
            start_time=start_time,
            end_time=end_time,
        )
    )

    # Try to create meeting for event2 - should be skipped due to dedup
    with patch(
        "reflector.worker.ics_sync.create_platform_client"
    ) as mock_platform_factory:
        mock_client = AsyncMock()
        mock_client.create_meeting.return_value = AsyncMock(
            meeting_id="meeting-2",
            room_name="dedup-test-room-def",
            room_url="https://mock.video/dedup-test-room-def",
            host_room_url="https://mock.video/dedup-test-room-def?host=true",
        )
        mock_client.upload_logo = AsyncMock()
        mock_platform_factory.return_value = mock_client

        await create_upcoming_meetings_for_event(event2, create_window, room)

        # Platform client should NOT have been called for the duplicate
        mock_client.create_meeting.assert_not_called()

    # Verify still only 1 meeting
    results = await get_database().fetch_all(
        meetings.select().where(meetings.c.room_id == room.id)
    )
    assert len(results) == 1, f"Expected 1 meeting after dedup, got {len(results)}"


@pytest.mark.asyncio
async def test_different_time_windows_create_separate_meetings():
    """Events at different times should create separate meetings, even if titles match."""

    room = await rooms_controller.add(
        name="dedup-diff-time-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/dedup2.ics",
        ics_enabled=True,
    )

    now = datetime.now(timezone.utc)
    create_window = now - timedelta(minutes=6)

    # Event 1: 1-2pm
    event1 = await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid="event-morning@Cal.com",
            title="Team Standup",
            start_time=now + timedelta(hours=1),
            end_time=now + timedelta(hours=2),
        )
    )

    # Event 2: 3-4pm (different time)
    event2 = await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid="event-afternoon@Cal.com",
            title="Team Standup",
            start_time=now + timedelta(hours=3),
            end_time=now + timedelta(hours=4),
        )
    )

    with patch(
        "reflector.worker.ics_sync.create_platform_client"
    ) as mock_platform_factory:
        mock_client = AsyncMock()

        call_count = 0

        async def mock_create_meeting(room_name_prefix, end_date, room):
            nonlocal call_count
            call_count += 1
            return AsyncMock(
                meeting_id=f"meeting-{call_count}",
                room_name=f"dedup-diff-time-room-{call_count}",
                room_url=f"https://mock.video/dedup-diff-time-room-{call_count}",
                host_room_url=f"https://mock.video/dedup-diff-time-room-{call_count}?host=true",
            )

        mock_client.create_meeting = mock_create_meeting
        mock_client.upload_logo = AsyncMock()
        mock_platform_factory.return_value = mock_client

        await create_upcoming_meetings_for_event(event1, create_window, room)
        await create_upcoming_meetings_for_event(event2, create_window, room)

    results = await get_database().fetch_all(
        meetings.select().where(meetings.c.room_id == room.id)
    )
    assert (
        len(results) == 2
    ), f"Expected 2 meetings for different times, got {len(results)}"
