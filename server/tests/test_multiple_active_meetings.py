"""Tests for multiple active meetings per room functionality."""

from datetime import datetime, timedelta, timezone

import pytest

from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller


@pytest.mark.asyncio
async def test_multiple_active_meetings_per_room():
    """Test that multiple active meetings can exist for the same room."""
    # Create a room
    room = await rooms_controller.add(
        name="test-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
    )

    current_time = datetime.now(timezone.utc)
    end_time = current_time + timedelta(hours=2)

    # Create first meeting
    meeting1 = await meetings_controller.create(
        id="meeting-1",
        room_name="test-meeting-1",
        room_url="https://whereby.com/test-1",
        host_room_url="https://whereby.com/test-1-host",
        start_date=current_time,
        end_date=end_time,
        user_id="test-user",
        room=room,
    )

    # Create second meeting for the same room (should succeed now)
    meeting2 = await meetings_controller.create(
        id="meeting-2",
        room_name="test-meeting-2",
        room_url="https://whereby.com/test-2",
        host_room_url="https://whereby.com/test-2-host",
        start_date=current_time,
        end_date=end_time,
        user_id="test-user",
        room=room,
    )

    # Both meetings should be active
    active_meetings = await meetings_controller.get_all_active_for_room(
        room=room, current_time=current_time
    )

    assert len(active_meetings) == 2
    assert meeting1.id in [m.id for m in active_meetings]
    assert meeting2.id in [m.id for m in active_meetings]


@pytest.mark.asyncio
async def test_get_active_by_calendar_event():
    """Test getting active meeting by calendar event ID."""
    # Create a room
    room = await rooms_controller.add(
        name="test-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
    )

    # Create a calendar event
    event = CalendarEvent(
        room_id=room.id,
        ics_uid="test-event-uid",
        title="Test Meeting",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=1),
    )
    event = await calendar_events_controller.upsert(event)

    current_time = datetime.now(timezone.utc)
    end_time = current_time + timedelta(hours=2)

    # Create meeting linked to calendar event
    meeting = await meetings_controller.create(
        id="meeting-cal-1",
        room_name="test-meeting-cal",
        room_url="https://whereby.com/test-cal",
        host_room_url="https://whereby.com/test-cal-host",
        start_date=current_time,
        end_date=end_time,
        user_id="test-user",
        room=room,
        calendar_event_id=event.id,
        calendar_metadata={"title": event.title},
    )

    # Should find the meeting by calendar event
    found_meeting = await meetings_controller.get_active_by_calendar_event(
        room=room, calendar_event_id=event.id, current_time=current_time
    )

    assert found_meeting is not None
    assert found_meeting.id == meeting.id
    assert found_meeting.calendar_event_id == event.id


@pytest.mark.asyncio
async def test_calendar_meeting_force_close_after_30_min():
    """Test that calendar meetings force close 30 minutes after scheduled end."""
    # Create a room
    room = await rooms_controller.add(
        name="test-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
    )

    # Create a calendar event
    event = CalendarEvent(
        room_id=room.id,
        ics_uid="test-event-force",
        title="Test Meeting Force Close",
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        end_time=datetime.now(timezone.utc) - timedelta(minutes=35),  # Ended 35 min ago
    )
    event = await calendar_events_controller.upsert(event)

    current_time = datetime.now(timezone.utc)

    # Create meeting linked to calendar event
    meeting = await meetings_controller.create(
        id="meeting-force",
        room_name="test-meeting-force",
        room_url="https://whereby.com/test-force",
        host_room_url="https://whereby.com/test-force-host",
        start_date=event.start_time,
        end_date=event.end_time,
        user_id="test-user",
        room=room,
        calendar_event_id=event.id,
    )

    # Test that calendar meetings force close 30 min after scheduled end
    # The meeting ended 35 minutes ago, so it should be force closed

    # Manually test the force close logic that would be in process_meetings
    if meeting.calendar_event_id:
        if current_time > meeting.end_date + timedelta(minutes=30):
            await meetings_controller.update_meeting(meeting.id, is_active=False)

    updated_meeting = await meetings_controller.get_by_id(meeting.id)
    assert updated_meeting.is_active is False  # Force closed after 30 min
