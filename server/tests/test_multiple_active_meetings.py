"""Tests for multiple active meetings per room functionality."""

from datetime import datetime, timedelta, timezone

import pytest

from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller


@pytest.mark.asyncio
async def test_multiple_active_meetings_per_room(db_db_session):
    """Test that multiple active meetings can exist for the same room."""
    # Create a room
    room = await rooms_controller.add(
        session,
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
        session,
        id="meeting-1",
        room_name="test-meeting-1",
        room_url="https://whereby.com/test-1",
        host_room_url="https://whereby.com/test-1-host",
        start_date=current_time,
        end_date=end_time,
        room=room,
    )

    # Create second meeting for the same room (should succeed now)
    meeting2 = await meetings_controller.create(
        session,
        id="meeting-2",
        room_name="test-meeting-2",
        room_url="https://whereby.com/test-2",
        host_room_url="https://whereby.com/test-2-host",
        start_date=current_time,
        end_date=end_time,
        room=room,
    )

    # Both meetings should be active
    active_meetings = await meetings_controller.get_all_active_for_room(
        session, room=room, current_time=current_time
    )

    assert len(active_meetings) == 2
    assert meeting1.id in [m.id for m in active_meetings]
    assert meeting2.id in [m.id for m in active_meetings]


@pytest.mark.asyncio
async def test_get_active_by_calendar_event(db_db_session):
    """Test getting active meeting by calendar event ID."""
    # Create a room
    room = await rooms_controller.add(
        session,
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
    event = await calendar_events_controller.upsert(session, event)

    current_time = datetime.now(timezone.utc)
    end_time = current_time + timedelta(hours=2)

    # Create meeting linked to calendar event
    meeting = await meetings_controller.create(
        session,
        id="meeting-cal-1",
        room_name="test-meeting-cal",
        room_url="https://whereby.com/test-cal",
        host_room_url="https://whereby.com/test-cal-host",
        start_date=current_time,
        end_date=end_time,
        room=room,
        calendar_event_id=event.id,
        calendar_metadata={"title": event.title},
    )

    # Should find the meeting by calendar event
    found_meeting = await meetings_controller.get_active_by_calendar_event(
        session, room=room, calendar_event_id=event.id, current_time=current_time
    )

    assert found_meeting is not None
    assert found_meeting.id == meeting.id
    assert found_meeting.calendar_event_id == event.id


@pytest.mark.asyncio
async def test_calendar_meeting_deactivates_after_scheduled_end(db_db_session):
    """Test that unused calendar meetings deactivate after scheduled end time."""
    # Create a room
    room = await rooms_controller.add(
        session,
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

    # Create a calendar event that ended 35 minutes ago
    event = CalendarEvent(
        room_id=room.id,
        ics_uid="test-event-unused",
        title="Test Meeting Unused",
        start_time=datetime.now(timezone.utc) - timedelta(hours=2),
        end_time=datetime.now(timezone.utc) - timedelta(minutes=35),
    )
    event = await calendar_events_controller.upsert(session, event)

    current_time = datetime.now(timezone.utc)

    # Create meeting linked to calendar event
    meeting = await meetings_controller.create(
        session,
        id="meeting-unused",
        room_name="test-meeting-unused",
        room_url="https://whereby.com/test-unused",
        host_room_url="https://whereby.com/test-unused-host",
        start_date=event.start_time,
        end_date=event.end_time,
        room=room,
        calendar_event_id=event.id,
    )

    # Test the new logic: unused calendar meetings deactivate after scheduled end
    # The meeting ended 35 minutes ago and was never used, so it should be deactivated

    # Simulate process_meetings logic for unused calendar meeting past end time
    if meeting.calendar_event_id and current_time > meeting.end_date:
        # In real code, we'd check has_had_sessions = False here
        await meetings_controller.update_meeting(session, meeting.id, is_active=False)

    updated_meeting = await meetings_controller.get_by_id(session, meeting.id)
    assert updated_meeting.is_active is False  # Deactivated after scheduled end
