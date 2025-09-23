from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from icalendar import Calendar, Event

from reflector.db.calendar_events import calendar_events_controller
from reflector.db.rooms import rooms_controller
from reflector.services.ics_sync import ics_sync_service
from reflector.worker.ics_sync import (
    _should_sync,
    sync_room_ics,
)


@pytest.mark.asyncio
async def test_sync_room_ics_task(session):
    room = await rooms_controller.add(
        session,
        name="task-test-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/task.ics",
        ics_enabled=True,
    )
    # Commit to make room visible to ICS service's separate session
    await session.commit()

    cal = Calendar()
    event = Event()
    event.add("uid", "task-event-1")
    event.add("summary", "Task Test Meeting")
    from reflector.settings import settings

    event.add("location", f"{settings.UI_BASE_URL}/{room.name}")
    now = datetime.now(timezone.utc)
    event.add("dtstart", now + timedelta(hours=1))
    event.add("dtend", now + timedelta(hours=2))
    cal.add_component(event)
    ics_content = cal.to_ical().decode("utf-8")

    with patch(
        "reflector.services.ics_sync.ICSFetchService.fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ics_content

        # Call the service directly instead of the Celery task to avoid event loop issues
        await ics_sync_service.sync_room_calendar(room)

        events = await calendar_events_controller.get_by_room(session, room.id)
        assert len(events) == 1
        assert events[0].ics_uid == "task-event-1"


@pytest.mark.asyncio
async def test_sync_room_ics_disabled(session):
    room = await rooms_controller.add(
        session,
        name="disabled-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_enabled=False,
    )

    # Test that disabled rooms are skipped by the service
    result = await ics_sync_service.sync_room_calendar(room)

    events = await calendar_events_controller.get_by_room(session, room.id)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_sync_all_ics_calendars(session):
    room1 = await rooms_controller.add(
        session,
        name="sync-all-1",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/1.ics",
        ics_enabled=True,
    )

    room2 = await rooms_controller.add(
        session,
        name="sync-all-2",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/2.ics",
        ics_enabled=True,
    )

    room3 = await rooms_controller.add(
        session,
        name="sync-all-3",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_enabled=False,
    )

    with patch("reflector.worker.ics_sync.sync_room_ics.delay") as mock_delay:
        # Directly call the sync_all logic without the Celery wrapper
        ics_enabled_rooms = await rooms_controller.get_ics_enabled(session)

        for room in ics_enabled_rooms:
            if room and _should_sync(room):
                sync_room_ics.delay(room.id)

        assert mock_delay.call_count == 2
        called_room_ids = [call.args[0] for call in mock_delay.call_args_list]
        assert room1.id in called_room_ids
        assert room2.id in called_room_ids
        assert room3.id not in called_room_ids


@pytest.mark.asyncio
async def test_should_sync_logic():
    room = MagicMock()

    room.ics_last_sync = None
    assert _should_sync(room) is True

    room.ics_last_sync = datetime.now(timezone.utc) - timedelta(seconds=100)
    room.ics_fetch_interval = 300
    assert _should_sync(room) is False

    room.ics_last_sync = datetime.now(timezone.utc) - timedelta(seconds=400)
    room.ics_fetch_interval = 300
    assert _should_sync(room) is True


@pytest.mark.asyncio
async def test_sync_respects_fetch_interval(session):
    now = datetime.now(timezone.utc)

    room1 = await rooms_controller.add(
        session,
        name="interval-test-1",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/interval.ics",
        ics_enabled=True,
        ics_fetch_interval=300,
    )

    await rooms_controller.update(
        session,
        room1,
        {"ics_last_sync": now - timedelta(seconds=100)},
    )

    room2 = await rooms_controller.add(
        session,
        name="interval-test-2",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/interval2.ics",
        ics_enabled=True,
        ics_fetch_interval=60,
    )

    await rooms_controller.update(
        session,
        room2,
        {"ics_last_sync": now - timedelta(seconds=100)},
    )

    with patch("reflector.worker.ics_sync.sync_room_ics.delay") as mock_delay:
        # Test the sync logic without the Celery wrapper
        ics_enabled_rooms = await rooms_controller.get_ics_enabled(session)

        for room in ics_enabled_rooms:
            if room and _should_sync(room):
                sync_room_ics.delay(room.id)

        assert mock_delay.call_count == 1
        assert mock_delay.call_args[0][0] == room2.id


@pytest.mark.asyncio
async def test_sync_handles_errors_gracefully(session):
    room = await rooms_controller.add(
        session,
        name="error-task-room",
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

    with patch(
        "reflector.services.ics_sync.ICSFetchService.fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.side_effect = Exception("Network error")

        # Call the service directly to test error handling
        result = await ics_sync_service.sync_room_calendar(room)
        assert result["status"] == "error"

        events = await calendar_events_controller.get_by_room(session, room.id)
        assert len(events) == 0
