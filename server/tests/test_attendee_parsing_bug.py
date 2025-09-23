import os
from unittest.mock import patch

import pytest

from reflector.db.rooms import rooms_controller
from reflector.services.ics_sync import ICSSyncService


@pytest.mark.asyncio
async def test_attendee_parsing_bug(db_session):
    """
    Test that reproduces the attendee parsing bug where a string with comma-separated
    emails gets parsed as individual characters instead of separate email addresses.

    The bug manifests as getting 29 attendees with emails like "M", "A", "I", etc.
    instead of properly parsed email addresses.
    """
    room = await rooms_controller.add(
        db_session,
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
        ics_url="http://test.com/test.ics",
        ics_enabled=True,
    )
    await db_session.flush()

    from datetime import datetime, timedelta, timezone

    test_ics_path = os.path.join(
        os.path.dirname(__file__), "test_attendee_parsing_bug.ics"
    )
    with open(test_ics_path, "r") as f:
        ics_content = f.read()

    now = datetime.now(timezone.utc)
    future_time = now + timedelta(hours=1)
    end_time = future_time + timedelta(hours=1)

    dtstart = future_time.strftime("%Y%m%dT%H%M%SZ")
    dtend = end_time.strftime("%Y%m%dT%H%M%SZ")
    dtstamp = now.strftime("%Y%m%dT%H%M%SZ")

    ics_content = ics_content.replace("20250910T180000Z", dtstart)
    ics_content = ics_content.replace("20250910T190000Z", dtend)
    ics_content = ics_content.replace("20250910T174000Z", dtstamp)

    sync_service = ICSSyncService()
    from contextlib import asynccontextmanager
    from unittest.mock import AsyncMock

    @asynccontextmanager
    async def mock_session_context():
        yield db_session

    class MockSessionMaker:
        def __call__(self):
            return mock_session_context()

    mock_session_factory = MockSessionMaker()

    with patch("reflector.services.ics_sync.get_session_factory") as mock_get_factory:
        mock_get_factory.return_value = mock_session_factory

        with patch.object(
            sync_service.fetch_service, "fetch_ics", new_callable=AsyncMock
        ) as mock_fetch:
            mock_fetch.return_value = ics_content

            calendar = sync_service.fetch_service.parse_ics(ics_content)
            from reflector.settings import settings

            room_url = f"{settings.UI_BASE_URL}/{room.name}"

            print(f"Room URL being used for matching: {room_url}")
            print(f"ICS content:\n{ics_content}")

            events, total_events = sync_service.fetch_service.extract_room_events(
                calendar, room.name, room_url
            )

            print(f"Total events in calendar: {total_events}")
            print(f"Events matching room: {len(events)}")

            result = await sync_service.sync_room_calendar(room)

            assert result.get("status") == "success"
            assert result.get("events_found", 0) >= 0

            assert len(events) == 1
            event = events[0]

        attendees = event["attendees"]

        print(f"Number of attendees: {len(attendees)}")
        for i, attendee in enumerate(attendees):
            print(f"Attendee {i}: {attendee}")

        assert len(attendees) == 30, f"Expected 30 attendees, got {len(attendees)}"

        assert attendees[0]["email"] == "alice@example.com"
        assert attendees[1]["email"] == "bob@example.com"
        assert attendees[2]["email"] == "charlie@example.com"
        assert any(att["email"] == "organizer@example.com" for att in attendees)
