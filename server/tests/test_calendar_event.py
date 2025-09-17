"""
Tests for CalendarEvent model.
"""

from datetime import datetime, timedelta, timezone

import pytest

from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.rooms import rooms_controller


@pytest.mark.asyncio
async def test_calendar_event_create():
    """Test creating a calendar event."""
    # Create a room first
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

    # Create calendar event
    now = datetime.now(timezone.utc)
    event = CalendarEvent(
        room_id=room.id,
        ics_uid="test-event-123",
        title="Team Meeting",
        description="Weekly team sync",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        location=f"https://example.com/{room.name}",
        attendees=[
            {"email": "alice@example.com", "name": "Alice", "status": "ACCEPTED"},
            {"email": "bob@example.com", "name": "Bob", "status": "TENTATIVE"},
        ],
    )

    # Save event
    saved_event = await calendar_events_controller.upsert(event)

    assert saved_event.ics_uid == "test-event-123"
    assert saved_event.title == "Team Meeting"
    assert saved_event.room_id == room.id
    assert len(saved_event.attendees) == 2


@pytest.mark.asyncio
async def test_calendar_event_get_by_room():
    """Test getting calendar events for a room."""
    # Create room
    room = await rooms_controller.add(
        name="events-room",
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

    now = datetime.now(timezone.utc)

    # Create multiple events
    for i in range(3):
        event = CalendarEvent(
            room_id=room.id,
            ics_uid=f"event-{i}",
            title=f"Meeting {i}",
            start_time=now + timedelta(hours=i),
            end_time=now + timedelta(hours=i + 1),
        )
        await calendar_events_controller.upsert(event)

    # Get events for room
    events = await calendar_events_controller.get_by_room(room.id)

    assert len(events) == 3
    assert all(e.room_id == room.id for e in events)
    assert events[0].title == "Meeting 0"
    assert events[1].title == "Meeting 1"
    assert events[2].title == "Meeting 2"


@pytest.mark.asyncio
async def test_calendar_event_get_upcoming():
    """Test getting upcoming events within time window."""
    # Create room
    room = await rooms_controller.add(
        name="upcoming-room",
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

    now = datetime.now(timezone.utc)

    # Create events at different times
    # Past event (should not be included)
    past_event = CalendarEvent(
        room_id=room.id,
        ics_uid="past-event",
        title="Past Meeting",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
    )
    await calendar_events_controller.upsert(past_event)

    # Upcoming event within 30 minutes
    upcoming_event = CalendarEvent(
        room_id=room.id,
        ics_uid="upcoming-event",
        title="Upcoming Meeting",
        start_time=now + timedelta(minutes=15),
        end_time=now + timedelta(minutes=45),
    )
    await calendar_events_controller.upsert(upcoming_event)

    # Currently happening event (started 10 minutes ago, ends in 20 minutes)
    current_event = CalendarEvent(
        room_id=room.id,
        ics_uid="current-event",
        title="Current Meeting",
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(minutes=20),
    )
    await calendar_events_controller.upsert(current_event)

    # Future event beyond 30 minutes
    future_event = CalendarEvent(
        room_id=room.id,
        ics_uid="future-event",
        title="Future Meeting",
        start_time=now + timedelta(hours=2),
        end_time=now + timedelta(hours=3),
    )
    await calendar_events_controller.upsert(future_event)

    # Get upcoming events (default 120 minutes) - should include current, upcoming, and future
    upcoming = await calendar_events_controller.get_upcoming(room.id)

    assert len(upcoming) == 3
    # Events should be sorted by start_time (current event first, then upcoming, then future)
    assert upcoming[0].ics_uid == "current-event"
    assert upcoming[1].ics_uid == "upcoming-event"
    assert upcoming[2].ics_uid == "future-event"

    # Get upcoming with custom window
    upcoming_extended = await calendar_events_controller.get_upcoming(
        room.id, minutes_ahead=180
    )

    assert len(upcoming_extended) == 3
    # Events should be sorted by start_time
    assert upcoming_extended[0].ics_uid == "current-event"
    assert upcoming_extended[1].ics_uid == "upcoming-event"
    assert upcoming_extended[2].ics_uid == "future-event"


@pytest.mark.asyncio
async def test_calendar_event_get_upcoming_includes_currently_happening():
    """Test that get_upcoming includes currently happening events but excludes ended events."""
    # Create room
    room = await rooms_controller.add(
        name="current-happening-room",
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

    now = datetime.now(timezone.utc)

    # Event that ended in the past (should NOT be included)
    past_ended_event = CalendarEvent(
        room_id=room.id,
        ics_uid="past-ended-event",
        title="Past Ended Meeting",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(minutes=30),
    )
    await calendar_events_controller.upsert(past_ended_event)

    # Event currently happening (started 10 minutes ago, ends in 20 minutes) - SHOULD be included
    currently_happening_event = CalendarEvent(
        room_id=room.id,
        ics_uid="currently-happening",
        title="Currently Happening Meeting",
        start_time=now - timedelta(minutes=10),
        end_time=now + timedelta(minutes=20),
    )
    await calendar_events_controller.upsert(currently_happening_event)

    # Event starting soon (in 5 minutes) - SHOULD be included
    upcoming_soon_event = CalendarEvent(
        room_id=room.id,
        ics_uid="upcoming-soon",
        title="Upcoming Soon Meeting",
        start_time=now + timedelta(minutes=5),
        end_time=now + timedelta(minutes=35),
    )
    await calendar_events_controller.upsert(upcoming_soon_event)

    # Get upcoming events
    upcoming = await calendar_events_controller.get_upcoming(room.id, minutes_ahead=30)

    # Should only include currently happening and upcoming soon events
    assert len(upcoming) == 2
    assert upcoming[0].ics_uid == "currently-happening"
    assert upcoming[1].ics_uid == "upcoming-soon"


@pytest.mark.asyncio
async def test_calendar_event_upsert():
    """Test upserting (create/update) calendar events."""
    # Create room
    room = await rooms_controller.add(
        name="upsert-room",
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

    now = datetime.now(timezone.utc)

    # Create new event
    event = CalendarEvent(
        room_id=room.id,
        ics_uid="upsert-test",
        title="Original Title",
        start_time=now,
        end_time=now + timedelta(hours=1),
    )

    created = await calendar_events_controller.upsert(event)
    assert created.title == "Original Title"

    # Update existing event
    event.title = "Updated Title"
    event.description = "Added description"

    updated = await calendar_events_controller.upsert(event)
    assert updated.title == "Updated Title"
    assert updated.description == "Added description"
    assert updated.ics_uid == "upsert-test"

    # Verify only one event exists
    events = await calendar_events_controller.get_by_room(room.id)
    assert len(events) == 1
    assert events[0].title == "Updated Title"


@pytest.mark.asyncio
async def test_calendar_event_soft_delete():
    """Test soft deleting events no longer in calendar."""
    # Create room
    room = await rooms_controller.add(
        name="delete-room",
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

    now = datetime.now(timezone.utc)

    # Create multiple events
    for i in range(4):
        event = CalendarEvent(
            room_id=room.id,
            ics_uid=f"event-{i}",
            title=f"Meeting {i}",
            start_time=now + timedelta(hours=i),
            end_time=now + timedelta(hours=i + 1),
        )
        await calendar_events_controller.upsert(event)

    # Soft delete events not in current list
    current_ids = ["event-0", "event-2"]  # Keep events 0 and 2
    deleted_count = await calendar_events_controller.soft_delete_missing(
        room.id, current_ids
    )

    assert deleted_count == 2  # Should delete events 1 and 3

    # Get non-deleted events
    events = await calendar_events_controller.get_by_room(
        room.id, include_deleted=False
    )
    assert len(events) == 2
    assert {e.ics_uid for e in events} == {"event-0", "event-2"}

    # Get all events including deleted
    all_events = await calendar_events_controller.get_by_room(
        room.id, include_deleted=True
    )
    assert len(all_events) == 4


@pytest.mark.asyncio
async def test_calendar_event_past_events_not_deleted():
    """Test that past events are not soft deleted."""
    # Create room
    room = await rooms_controller.add(
        name="past-events-room",
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

    now = datetime.now(timezone.utc)

    # Create past event
    past_event = CalendarEvent(
        room_id=room.id,
        ics_uid="past-event",
        title="Past Meeting",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
    )
    await calendar_events_controller.upsert(past_event)

    # Create future event
    future_event = CalendarEvent(
        room_id=room.id,
        ics_uid="future-event",
        title="Future Meeting",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
    )
    await calendar_events_controller.upsert(future_event)

    # Try to soft delete all events (only future should be deleted)
    deleted_count = await calendar_events_controller.soft_delete_missing(room.id, [])

    assert deleted_count == 1  # Only future event deleted

    # Verify past event still exists
    events = await calendar_events_controller.get_by_room(
        room.id, include_deleted=False
    )
    assert len(events) == 1
    assert events[0].ics_uid == "past-event"


@pytest.mark.asyncio
async def test_calendar_event_with_raw_ics_data():
    """Test storing raw ICS data with calendar event."""
    # Create room
    room = await rooms_controller.add(
        name="raw-ics-room",
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

    raw_ics = """BEGIN:VEVENT
UID:test-raw-123
SUMMARY:Test Event
DTSTART:20240101T100000Z
DTEND:20240101T110000Z
END:VEVENT"""

    event = CalendarEvent(
        room_id=room.id,
        ics_uid="test-raw-123",
        title="Test Event",
        start_time=datetime.now(timezone.utc),
        end_time=datetime.now(timezone.utc) + timedelta(hours=1),
        ics_raw_data=raw_ics,
    )

    saved = await calendar_events_controller.upsert(event)

    assert saved.ics_raw_data == raw_ics

    # Retrieve and verify
    retrieved = await calendar_events_controller.get_by_ics_uid(room.id, "test-raw-123")
    assert retrieved is not None
    assert retrieved.ics_raw_data == raw_ics
