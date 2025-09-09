from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from icalendar import Calendar, Event

from reflector.db.calendar_events import CalendarEvent, calendar_events_controller
from reflector.db.rooms import rooms_controller


@pytest.fixture
async def authenticated_client(client):
    from reflector.app import app
    from reflector.auth import current_user_optional

    app.dependency_overrides[current_user_optional] = lambda: {
        "sub": "test-user",
        "email": "test@example.com",
    }
    yield client
    del app.dependency_overrides[current_user_optional]


@pytest.mark.asyncio
async def test_create_room_with_ics_fields(authenticated_client):
    client = authenticated_client
    response = await client.post(
        "/rooms",
        json={
            "name": "test-ics-room",
            "zulip_auto_post": False,
            "zulip_stream": "",
            "zulip_topic": "",
            "is_locked": False,
            "room_mode": "normal",
            "recording_type": "cloud",
            "recording_trigger": "automatic-2nd-participant",
            "is_shared": False,
            "ics_url": "https://calendar.example.com/test.ics",
            "ics_fetch_interval": 600,
            "ics_enabled": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test-ics-room"
    assert data["ics_url"] == "https://calendar.example.com/test.ics"
    assert data["ics_fetch_interval"] == 600
    assert data["ics_enabled"] is True


@pytest.mark.asyncio
async def test_update_room_ics_configuration(authenticated_client):
    client = authenticated_client
    response = await client.post(
        "/rooms",
        json={
            "name": "update-ics-room",
            "zulip_auto_post": False,
            "zulip_stream": "",
            "zulip_topic": "",
            "is_locked": False,
            "room_mode": "normal",
            "recording_type": "cloud",
            "recording_trigger": "automatic-2nd-participant",
            "is_shared": False,
        },
    )
    assert response.status_code == 200
    room_id = response.json()["id"]

    response = await client.patch(
        f"/rooms/{room_id}",
        json={
            "ics_url": "https://calendar.google.com/updated.ics",
            "ics_fetch_interval": 300,
            "ics_enabled": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["ics_url"] == "https://calendar.google.com/updated.ics"
    assert data["ics_fetch_interval"] == 300
    assert data["ics_enabled"] is True


@pytest.mark.asyncio
async def test_trigger_ics_sync(authenticated_client):
    client = authenticated_client
    room = await rooms_controller.add(
        name="sync-api-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/api.ics",
        ics_enabled=True,
    )

    cal = Calendar()
    event = Event()
    event.add("uid", "api-test-event")
    event.add("summary", "API Test Meeting")
    from reflector.settings import settings

    event.add("location", f"{settings.BASE_URL}/{room.name}")
    now = datetime.now(timezone.utc)
    event.add("dtstart", now + timedelta(hours=1))
    event.add("dtend", now + timedelta(hours=2))
    cal.add_component(event)
    ics_content = cal.to_ical().decode("utf-8")

    with patch(
        "reflector.services.ics_sync.ICSFetchService.fetch_ics", new_callable=AsyncMock
    ) as mock_fetch:
        mock_fetch.return_value = ics_content

        response = await client.post(f"/rooms/{room.name}/ics/sync")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["events_found"] == 1
        assert data["events_created"] == 1


@pytest.mark.asyncio
async def test_trigger_ics_sync_unauthorized(client):
    room = await rooms_controller.add(
        name="sync-unauth-room",
        user_id="owner-123",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/api.ics",
        ics_enabled=True,
    )

    response = await client.post(f"/rooms/{room.name}/ics/sync")
    assert response.status_code == 403
    assert "Only room owner can trigger ICS sync" in response.json()["detail"]


@pytest.mark.asyncio
async def test_trigger_ics_sync_not_configured(authenticated_client):
    client = authenticated_client
    room = await rooms_controller.add(
        name="sync-not-configured",
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

    response = await client.post(f"/rooms/{room.name}/ics/sync")
    assert response.status_code == 400
    assert "ICS not configured" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_ics_status(authenticated_client):
    client = authenticated_client
    room = await rooms_controller.add(
        name="status-room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/status.ics",
        ics_enabled=True,
        ics_fetch_interval=300,
    )

    now = datetime.now(timezone.utc)
    await rooms_controller.update(
        room,
        {"ics_last_sync": now, "ics_last_etag": "test-etag"},
    )

    response = await client.get(f"/rooms/{room.name}/ics/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "enabled"
    assert data["last_etag"] == "test-etag"
    assert data["events_count"] == 0


@pytest.mark.asyncio
async def test_get_ics_status_unauthorized(client):
    room = await rooms_controller.add(
        name="status-unauth",
        user_id="owner-456",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="https://calendar.example.com/status.ics",
        ics_enabled=True,
    )

    response = await client.get(f"/rooms/{room.name}/ics/status")
    assert response.status_code == 403
    assert "Only room owner can view ICS status" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_room_meetings(authenticated_client):
    client = authenticated_client
    room = await rooms_controller.add(
        name="meetings-room",
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
    event1 = CalendarEvent(
        room_id=room.id,
        ics_uid="meeting-1",
        title="Past Meeting",
        start_time=now - timedelta(hours=2),
        end_time=now - timedelta(hours=1),
    )
    await calendar_events_controller.upsert(event1)

    event2 = CalendarEvent(
        room_id=room.id,
        ics_uid="meeting-2",
        title="Future Meeting",
        description="Team sync",
        start_time=now + timedelta(hours=1),
        end_time=now + timedelta(hours=2),
        attendees=[{"email": "test@example.com"}],
    )
    await calendar_events_controller.upsert(event2)

    response = await client.get(f"/rooms/{room.name}/meetings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Past Meeting"
    assert data[1]["title"] == "Future Meeting"
    assert data[1]["description"] == "Team sync"
    assert data[1]["attendees"] == [{"email": "test@example.com"}]


@pytest.mark.asyncio
async def test_list_room_meetings_non_owner(client):
    room = await rooms_controller.add(
        name="meetings-privacy",
        user_id="owner-789",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
    )

    event = CalendarEvent(
        room_id=room.id,
        ics_uid="private-meeting",
        title="Meeting Title",
        description="Sensitive info",
        start_time=datetime.now(timezone.utc) + timedelta(hours=1),
        end_time=datetime.now(timezone.utc) + timedelta(hours=2),
        attendees=[{"email": "private@example.com"}],
    )
    await calendar_events_controller.upsert(event)

    response = await client.get(f"/rooms/{room.name}/meetings")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Meeting Title"
    assert data[0]["description"] is None
    assert data[0]["attendees"] is None


@pytest.mark.asyncio
async def test_list_upcoming_meetings(authenticated_client):
    client = authenticated_client
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

    past_event = CalendarEvent(
        room_id=room.id,
        ics_uid="past",
        title="Past",
        start_time=now - timedelta(hours=1),
        end_time=now - timedelta(minutes=30),
    )
    await calendar_events_controller.upsert(past_event)

    soon_event = CalendarEvent(
        room_id=room.id,
        ics_uid="soon",
        title="Soon",
        start_time=now + timedelta(minutes=15),
        end_time=now + timedelta(minutes=45),
    )
    await calendar_events_controller.upsert(soon_event)

    later_event = CalendarEvent(
        room_id=room.id,
        ics_uid="later",
        title="Later",
        start_time=now + timedelta(hours=2),
        end_time=now + timedelta(hours=3),
    )
    await calendar_events_controller.upsert(later_event)

    response = await client.get(f"/rooms/{room.name}/meetings/upcoming")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Soon"

    response = await client.get(
        f"/rooms/{room.name}/meetings/upcoming", params={"minutes_ahead": 180}
    )
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Soon"
    assert data[1]["title"] == "Later"


@pytest.mark.asyncio
async def test_room_not_found_endpoints(client):
    response = await client.post("/rooms/nonexistent/ics/sync")
    assert response.status_code == 404

    response = await client.get("/rooms/nonexistent/ics/status")
    assert response.status_code == 404

    response = await client.get("/rooms/nonexistent/meetings")
    assert response.status_code == 404

    response = await client.get("/rooms/nonexistent/meetings/upcoming")
    assert response.status_code == 404
