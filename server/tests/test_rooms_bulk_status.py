from datetime import datetime, timedelta, timezone

import pytest
from conftest import authenticated_client_ctx

from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import Room, rooms_controller
from reflector.settings import settings


async def _create_room(name: str, user_id: str, is_shared: bool = False) -> Room:
    return await rooms_controller.add(
        name=name,
        user_id=user_id,
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=is_shared,
        webhook_url="",
        webhook_secret="",
    )


async def _create_meeting(room: Room, active: bool = True):
    now = datetime.now(timezone.utc)
    return await meetings_controller.create(
        id=f"meeting-{room.name}-{now.timestamp()}",
        room_name=room.name,
        room_url="room-url",
        host_room_url="host-url",
        start_date=now - timedelta(minutes=10),
        end_date=now + timedelta(minutes=50) if active else now - timedelta(minutes=1),
        room=room,
    )


async def _create_calendar_event(room: Room):
    now = datetime.now(timezone.utc)
    return await calendar_events_controller.upsert(
        CalendarEvent(
            room_id=room.id,
            ics_uid=f"event-{room.name}",
            title=f"Upcoming in {room.name}",
            description="secret description",
            start_time=now + timedelta(minutes=30),
            end_time=now + timedelta(minutes=90),
            attendees=[{"name": "Alice", "email": "alice@example.com"}],
        )
    )


@pytest.mark.asyncio
async def test_bulk_status_returns_empty_for_no_rooms(client):
    """Empty room_names returns empty dict."""
    async with authenticated_client_ctx():
        resp = await client.post("/rooms/meetings/bulk-status", json={"room_names": []})
    assert resp.status_code == 200
    assert resp.json() == {}


@pytest.mark.asyncio
async def test_bulk_status_returns_active_meetings_and_upcoming_events(client):
    """Owner sees active meetings and upcoming events for their rooms."""
    room = await _create_room("bulk-test-room", "randomuserid")
    await _create_meeting(room, active=True)
    await _create_calendar_event(room)

    async with authenticated_client_ctx():
        resp = await client.post(
            "/rooms/meetings/bulk-status",
            json={"room_names": ["bulk-test-room"]},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert "bulk-test-room" in data
    status = data["bulk-test-room"]
    assert len(status["active_meetings"]) == 1
    assert len(status["upcoming_events"]) == 1
    # Owner sees description
    assert status["upcoming_events"][0]["description"] == "secret description"


@pytest.mark.asyncio
async def test_bulk_status_redacts_data_for_non_owner(client):
    """Non-owner of a shared room gets redacted calendar events and no whereby host_room_url."""
    room = await _create_room("shared-bulk", "other-user-id", is_shared=True)
    await _create_meeting(room, active=True)
    await _create_calendar_event(room)

    # authenticated as "randomuserid" but room owned by "other-user-id"
    async with authenticated_client_ctx():
        resp = await client.post(
            "/rooms/meetings/bulk-status",
            json={"room_names": ["shared-bulk"]},
        )

    assert resp.status_code == 200
    status = resp.json()["shared-bulk"]
    assert len(status["active_meetings"]) == 1
    assert len(status["upcoming_events"]) == 1
    # Non-owner: description and attendees redacted
    assert status["upcoming_events"][0]["description"] is None
    assert status["upcoming_events"][0]["attendees"] is None


@pytest.mark.asyncio
async def test_bulk_status_filters_private_rooms_of_other_users(client):
    """User cannot see private rooms owned by others."""
    await _create_room("private-other", "other-user-id", is_shared=False)

    async with authenticated_client_ctx():
        resp = await client.post(
            "/rooms/meetings/bulk-status",
            json={"room_names": ["private-other"]},
        )

    assert resp.status_code == 200
    status = resp.json()["private-other"]
    assert status["active_meetings"] == []
    assert status["upcoming_events"] == []


@pytest.mark.asyncio
async def test_bulk_status_redacts_whereby_host_room_url_for_non_owner(client):
    """Non-owner of a shared whereby room gets empty host_room_url."""
    room = await _create_room("shared-whereby", "other-user-id", is_shared=True)
    # Force platform to whereby
    from reflector.db import get_database
    from reflector.db.rooms import rooms as rooms_table

    await get_database().execute(
        rooms_table.update()
        .where(rooms_table.c.id == room.id)
        .values(platform="whereby")
    )

    await _create_meeting(room, active=True)

    async with authenticated_client_ctx():
        resp = await client.post(
            "/rooms/meetings/bulk-status",
            json={"room_names": ["shared-whereby"]},
        )

    assert resp.status_code == 200
    status = resp.json()["shared-whereby"]
    assert len(status["active_meetings"]) == 1
    assert status["active_meetings"][0]["host_room_url"] == ""


@pytest.mark.asyncio
async def test_bulk_status_unauthenticated_rejected_non_public(client):
    """Unauthenticated request on non-PUBLIC_MODE instance returns 401."""
    original = settings.PUBLIC_MODE
    try:
        settings.PUBLIC_MODE = False
        resp = await client.post(
            "/rooms/meetings/bulk-status",
            json={"room_names": ["any-room"]},
        )
        assert resp.status_code == 401
    finally:
        settings.PUBLIC_MODE = original


@pytest.mark.asyncio
async def test_bulk_status_nonexistent_room_returns_empty(client):
    """Requesting a room that doesn't exist returns empty lists."""
    async with authenticated_client_ctx():
        resp = await client.post(
            "/rooms/meetings/bulk-status",
            json={"room_names": ["does-not-exist"]},
        )

    assert resp.status_code == 200
    status = resp.json()["does-not-exist"]
    assert status["active_meetings"] == []
    assert status["upcoming_events"] == []
