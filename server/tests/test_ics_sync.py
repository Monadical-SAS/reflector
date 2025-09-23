from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from icalendar import Calendar, Event

from reflector.db.calendar_events import calendar_events_controller
from reflector.db.rooms import rooms_controller
from reflector.services.ics_sync import ICSFetchService, ICSSyncService


@pytest.mark.asyncio
async def test_ics_fetch_service_event_matching():
    service = ICSFetchService()
    room_name = "test-room"
    room_url = "https://example.com/test-room"

    # Create test event
    event = Event()
    event.add("uid", "test-123")
    event.add("summary", "Test Meeting")

    # Test matching with full URL in location
    event.add("location", "https://example.com/test-room")
    assert service._event_matches_room(event, room_name, room_url) is True

    # Test non-matching with URL without protocol (exact matching only now)
    event["location"] = "example.com/test-room"
    assert service._event_matches_room(event, room_name, room_url) is False

    # Test matching in description
    event["location"] = "Conference Room A"
    event.add("description", f"Join at {room_url}")
    assert service._event_matches_room(event, room_name, room_url) is True

    # Test non-matching
    event["location"] = "Different Room"
    event["description"] = "No room URL here"
    assert service._event_matches_room(event, room_name, room_url) is False

    # Test partial paths should NOT match anymore
    event["location"] = "/test-room"
    assert service._event_matches_room(event, room_name, room_url) is False

    event["location"] = f"Room: {room_name}"
    assert service._event_matches_room(event, room_name, room_url) is False


@pytest.mark.asyncio
async def test_ics_fetch_service_parse_event():
    service = ICSFetchService()

    # Create test event
    event = Event()
    event.add("uid", "test-456")
    event.add("summary", "Team Standup")
    event.add("description", "Daily team sync")
    event.add("location", "https://example.com/standup")

    now = datetime.now(timezone.utc)
    event.add("dtstart", now)
    event.add("dtend", now + timedelta(hours=1))

    # Add attendees
    event.add("attendee", "mailto:alice@example.com", parameters={"CN": "Alice"})
    event.add("attendee", "mailto:bob@example.com", parameters={"CN": "Bob"})
    event.add("organizer", "mailto:carol@example.com", parameters={"CN": "Carol"})

    # Parse event
    result = service._parse_event(event)

    assert result is not None
    assert result["ics_uid"] == "test-456"
    assert result["title"] == "Team Standup"
    assert result["description"] == "Daily team sync"
    assert result["location"] == "https://example.com/standup"
    assert len(result["attendees"]) == 3  # 2 attendees + 1 organizer


@pytest.mark.asyncio
async def test_ics_fetch_service_extract_room_events():
    service = ICSFetchService()
    room_name = "meeting"
    room_url = "https://example.com/meeting"

    # Create calendar with multiple events
    cal = Calendar()

    # Event 1: Matches room
    event1 = Event()
    event1.add("uid", "match-1")
    event1.add("summary", "Planning Meeting")
    event1.add("location", room_url)
    now = datetime.now(timezone.utc)
    event1.add("dtstart", now + timedelta(hours=2))
    event1.add("dtend", now + timedelta(hours=3))
    cal.add_component(event1)

    # Event 2: Doesn't match room
    event2 = Event()
    event2.add("uid", "no-match")
    event2.add("summary", "Other Meeting")
    event2.add("location", "https://example.com/other")
    event2.add("dtstart", now + timedelta(hours=4))
    event2.add("dtend", now + timedelta(hours=5))
    cal.add_component(event2)

    # Event 3: Matches room in description
    event3 = Event()
    event3.add("uid", "match-2")
    event3.add("summary", "Review Session")
    event3.add("description", f"Meeting link: {room_url}")
    event3.add("dtstart", now + timedelta(hours=6))
    event3.add("dtend", now + timedelta(hours=7))
    cal.add_component(event3)

    # Event 4: Cancelled event (should be skipped)
    event4 = Event()
    event4.add("uid", "cancelled")
    event4.add("summary", "Cancelled Meeting")
    event4.add("location", room_url)
    event4.add("status", "CANCELLED")
    event4.add("dtstart", now + timedelta(hours=8))
    event4.add("dtend", now + timedelta(hours=9))
    cal.add_component(event4)

    # Extract events
    events, total_events = service.extract_room_events(cal, room_name, room_url)

    assert len(events) == 2
    assert total_events == 3  # 3 events in time window (excluding cancelled)
    assert events[0]["ics_uid"] == "match-1"
    assert events[1]["ics_uid"] == "match-2"


@pytest.mark.asyncio
async def test_ics_sync_service_sync_room_calendar(db_session):
    # Create room
    room = await rooms_controller.add(
        db_session,
        name="sync-test",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/test.ics",
        ics_enabled=True,
    )
    await db_session.flush()

    # Mock ICS content
    cal = Calendar()
    event = Event()
    event.add("uid", "sync-event-1")
    event.add("summary", "Sync Test Meeting")
    # Use the actual UI_BASE_URL from settings
    from reflector.settings import settings

    event.add("location", f"{settings.UI_BASE_URL}/{room.name}")
    now = datetime.now(timezone.utc)
    event.add("dtstart", now + timedelta(hours=1))
    event.add("dtend", now + timedelta(hours=2))
    cal.add_component(event)
    ics_content = cal.to_ical().decode("utf-8")

    # Create sync service and mock fetch
    sync_service = ICSSyncService()

    with patch.object(
        sync_service.fetch_service, "fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ics_content

        # First sync
        result = await sync_service.sync_room_calendar(db_session, room)

        assert result["status"] == "success"
        assert result["events_found"] == 1
        assert result["events_created"] == 1
        assert result["events_updated"] == 0
        assert result["events_deleted"] == 0

        # Verify event was created
        events = await calendar_events_controller.get_by_room(db_session, room.id)
        assert len(events) == 1
        assert events[0].ics_uid == "sync-event-1"
        assert events[0].title == "Sync Test Meeting"

        # Second sync with same content (should be unchanged)
        # Refresh room to get updated etag and force sync by setting old sync time
        room = await rooms_controller.get_by_id(db_session, room.id)
        await rooms_controller.update(
            db_session,
            room,
            {"ics_last_sync": datetime.now(timezone.utc) - timedelta(minutes=10)},
        )
        result = await sync_service.sync_room_calendar(db_session, room)
        assert result["status"] == "unchanged"

        # Third sync with updated event
        event["summary"] = "Updated Meeting Title"
        cal = Calendar()
        cal.add_component(event)
        ics_content = cal.to_ical().decode("utf-8")
        mock_fetch.return_value = ics_content

        # Force sync by clearing etag
        await rooms_controller.update(db_session, room, {"ics_last_etag": None})

        result = await sync_service.sync_room_calendar(db_session, room)
        assert result["status"] == "success"
        assert result["events_created"] == 0
        assert result["events_updated"] == 1

        # Verify event was updated
        events = await calendar_events_controller.get_by_room(db_session, room.id)
        assert len(events) == 1
        assert events[0].title == "Updated Meeting Title"


@pytest.mark.asyncio
async def test_ics_sync_service_should_sync():
    service = ICSSyncService()

    # Room never synced
    room = MagicMock()
    room.ics_last_sync = None
    room.ics_fetch_interval = 300
    assert service._should_sync(room) is True

    # Room synced recently
    room.ics_last_sync = datetime.now(timezone.utc) - timedelta(seconds=100)
    assert service._should_sync(room) is False

    # Room sync due
    room.ics_last_sync = datetime.now(timezone.utc) - timedelta(seconds=400)
    assert service._should_sync(room) is True


@pytest.mark.asyncio
async def test_ics_sync_service_skip_disabled():
    service = ICSSyncService()

    # Room with ICS disabled
    room = MagicMock()
    room.ics_enabled = False
    room.ics_url = "https://calendar.example.com/test.ics"

    result = await service.sync_room_calendar(MagicMock(), room)
    assert result["status"] == "skipped"
    assert result["reason"] == "ICS not configured"

    # Room without URL
    room.ics_enabled = True
    room.ics_url = None

    result = await service.sync_room_calendar(MagicMock(), room)
    assert result["status"] == "skipped"
    assert result["reason"] == "ICS not configured"


@pytest.mark.asyncio
async def test_ics_sync_service_error_handling(db_session):
    # Create room
    room = await rooms_controller.add(
        db_session,
        name="error-test",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/error.ics",
        ics_enabled=True,
    )
    await db_session.flush()

    sync_service = ICSSyncService()

    with patch.object(
        sync_service.fetch_service, "fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")

        result = await sync_service.sync_room_calendar(db_session, room)
        assert result["status"] == "error"
        assert "Network error" in result["error"]
