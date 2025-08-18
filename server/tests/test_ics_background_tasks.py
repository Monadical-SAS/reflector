from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from icalendar import Calendar, Event

from reflector.db.calendar_events import calendar_events_controller
from reflector.db.rooms import rooms_controller
from reflector.worker.ics_sync import (
    _should_sync,
    _sync_all_ics_calendars_async,
    _sync_room_ics_async,
)


@pytest.mark.asyncio
async def test_sync_room_ics_task():
    room = await rooms_controller.add(
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

    cal = Calendar()
    event = Event()
    event.add("uid", "task-event-1")
    event.add("summary", "Task Test Meeting")
    from reflector.settings import settings

    event.add("location", f"{settings.BASE_URL}/room/{room.name}")
    now = datetime.now(timezone.utc)
    event.add("dtstart", now + timedelta(hours=1))
    event.add("dtend", now + timedelta(hours=2))
    cal.add_component(event)
    ics_content = cal.to_ical().decode("utf-8")

    with patch(
        "reflector.services.ics_sync.ICSFetchService.fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ics_content

        await _sync_room_ics_async(room.id)

        events = await calendar_events_controller.get_by_room(room.id)
        assert len(events) == 1
        assert events[0].ics_uid == "task-event-1"


@pytest.mark.asyncio
async def test_sync_room_ics_disabled():
    room = await rooms_controller.add(
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

    await _sync_room_ics_async(room.id)

    events = await calendar_events_controller.get_by_room(room.id)
    assert len(events) == 0


@pytest.mark.asyncio
async def test_sync_all_ics_calendars():
    room1 = await rooms_controller.add(
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
        await _sync_all_ics_calendars_async()

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
async def test_sync_respects_fetch_interval():
    now = datetime.now(timezone.utc)

    room1 = await rooms_controller.add(
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
        room1,
        {"ics_last_sync": now - timedelta(seconds=100)},
    )

    room2 = await rooms_controller.add(
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
        room2,
        {"ics_last_sync": now - timedelta(seconds=100)},
    )

    with patch("reflector.worker.ics_sync.sync_room_ics.delay") as mock_delay:
        await _sync_all_ics_calendars_async()

        assert mock_delay.call_count == 1
        assert mock_delay.call_args[0][0] == room2.id


@pytest.mark.asyncio
async def test_sync_handles_errors_gracefully():
    room = await rooms_controller.add(
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

        await _sync_room_ics_async(room.id)

        events = await calendar_events_controller.get_by_room(room.id)
        assert len(events) == 0
