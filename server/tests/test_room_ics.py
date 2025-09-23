"""
Tests for Room model ICS calendar integration fields.
"""

from datetime import datetime, timezone

import pytest

from reflector.db.rooms import rooms_controller


@pytest.mark.asyncio
async def test_room_create_with_ics_fields(db_db_session):
    """Test creating a room with ICS calendar fields."""
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
        ics_url="https://calendar.google.com/calendar/ical/test/private-token/basic.ics",
        ics_fetch_interval=600,
        ics_enabled=True,
    )

    assert room.name == "test-room"
    assert (
        room.ics_url
        == "https://calendar.google.com/calendar/ical/test/private-token/basic.ics"
    )
    assert room.ics_fetch_interval == 600
    assert room.ics_enabled is True
    assert room.ics_last_sync is None
    assert room.ics_last_etag is None


@pytest.mark.asyncio
async def test_room_update_ics_configuration(db_db_session):
    """Test updating room ICS configuration."""
    # Create room without ICS
    room = await rooms_controller.add(
        session,
        name="update-test",
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

    assert room.ics_enabled is False
    assert room.ics_url is None

    # Update with ICS configuration
    await rooms_controller.update(
        session,
        room,
        {
            "ics_url": "https://outlook.office365.com/owa/calendar/test/calendar.ics",
            "ics_fetch_interval": 300,
            "ics_enabled": True,
        },
    )

    assert (
        room.ics_url == "https://outlook.office365.com/owa/calendar/test/calendar.ics"
    )
    assert room.ics_fetch_interval == 300
    assert room.ics_enabled is True


@pytest.mark.asyncio
async def test_room_ics_sync_metadata(db_db_session):
    """Test updating room ICS sync metadata."""
    room = await rooms_controller.add(
        session,
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
        ics_url="https://example.com/calendar.ics",
        ics_enabled=True,
    )

    # Update sync metadata
    sync_time = datetime.now(timezone.utc)
    await rooms_controller.update(
        session,
        room,
        {
            "ics_last_sync": sync_time,
            "ics_last_etag": "abc123hash",
        },
    )

    assert room.ics_last_sync == sync_time
    assert room.ics_last_etag == "abc123hash"


@pytest.mark.asyncio
async def test_room_get_with_ics_fields(db_db_session):
    """Test retrieving room with ICS fields."""
    # Create room
    created_room = await rooms_controller.add(
        session,
        name="get-test",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        ics_url="webcal://calendar.example.com/feed.ics",
        ics_fetch_interval=900,
        ics_enabled=True,
    )

    # Get by ID
    room = await rooms_controller.get_by_id(session, created_room.id)
    assert room is not None
    assert room.ics_url == "webcal://calendar.example.com/feed.ics"
    assert room.ics_fetch_interval == 900
    assert room.ics_enabled is True

    # Get by name
    room = await rooms_controller.get_by_name(session, "get-test")
    assert room is not None
    assert room.ics_url == "webcal://calendar.example.com/feed.ics"
    assert room.ics_fetch_interval == 900
    assert room.ics_enabled is True


@pytest.mark.asyncio
async def test_room_list_with_ics_enabled_filter(db_db_session):
    """Test listing rooms filtered by ICS enabled status."""
    # Create rooms with and without ICS
    room1 = await rooms_controller.add(
        session,
        name="ics-enabled-1",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=True,
        ics_enabled=True,
        ics_url="https://calendar1.example.com/feed.ics",
    )

    room2 = await rooms_controller.add(
        session,
        name="ics-disabled",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=True,
        ics_enabled=False,
    )

    room3 = await rooms_controller.add(
        session,
        name="ics-enabled-2",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=True,
        ics_enabled=True,
        ics_url="https://calendar2.example.com/feed.ics",
    )

    # Get all rooms
    all_rooms = await rooms_controller.get_all(session)
    assert len(all_rooms) == 3

    # Filter for ICS-enabled rooms (would need to implement this in controller)
    ics_rooms = [r for r in all_rooms if r.ics_enabled]
    assert len(ics_rooms) == 2
    assert all(r.ics_enabled for r in ics_rooms)


@pytest.mark.asyncio
async def test_room_default_ics_values(db_db_session):
    """Test that ICS fields have correct default values."""
    room = await rooms_controller.add(
        session,
        name="default-test",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        # Don't specify ICS fields
    )

    assert room.ics_url is None
    assert room.ics_fetch_interval == 300  # Default 5 minutes
    assert room.ics_enabled is False
    assert room.ics_last_sync is None
    assert room.ics_last_etag is None
