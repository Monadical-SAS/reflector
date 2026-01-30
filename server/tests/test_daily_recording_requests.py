from datetime import datetime, timezone
from uuid import UUID

import pytest

from reflector.db.daily_recording_requests import (
    DailyRecordingRequest,
    daily_recording_requests_controller,
)
from reflector.db.meetings import Meeting, meetings_controller
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.rooms import Room, rooms_controller


@pytest.mark.asyncio
async def test_create_request():
    """Test creating a recording request."""
    # Create meeting first
    room = Room(id="test-room", name="Test Room", slug="test-room", user_id="test-user")
    await rooms_controller.create(room)

    meeting = Meeting(
        id="meeting-123",
        room_name="test-room",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="cloud",
    )
    await meetings_controller.create(meeting)

    request = DailyRecordingRequest(
        recording_id="rec-1",
        meeting_id="meeting-123",
        instance_id=UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890"),
        type="cloud",
        requested_at=datetime.now(timezone.utc),
    )

    await daily_recording_requests_controller.create(request)

    result = await daily_recording_requests_controller.find_by_recording_id("rec-1")
    assert result is not None
    assert result[0] == "meeting-123"
    assert result[1] == "cloud"


@pytest.mark.asyncio
async def test_multiple_recordings_same_meeting():
    """Test stop/restart creates multiple request rows."""
    # Create room and meeting
    room = Room(
        id="test-room-2", name="Test Room 2", slug="test-room-2", user_id="test-user"
    )
    await rooms_controller.create(room)

    meeting_id = "meeting-456"
    meeting = Meeting(
        id=meeting_id,
        room_name="test-room-2",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="cloud",
    )
    await meetings_controller.create(meeting)

    instance_id = UUID("b1c2d3e4-f5a6-7890-abcd-ef1234567890")

    # First recording
    await daily_recording_requests_controller.create(
        DailyRecordingRequest(
            recording_id="rec-1",
            meeting_id=meeting_id,
            instance_id=instance_id,
            type="cloud",
            requested_at=datetime.now(timezone.utc),
        )
    )

    # Stop, then restart (new recording_id, same instance_id)
    await daily_recording_requests_controller.create(
        DailyRecordingRequest(
            recording_id="rec-2",  # DIFFERENT
            meeting_id=meeting_id,
            instance_id=instance_id,  # SAME
            type="cloud",
            requested_at=datetime.now(timezone.utc),
        )
    )

    # Both exist
    requests = await daily_recording_requests_controller.get_by_meeting_id(meeting_id)
    assert len(requests) == 2
    assert {r.recording_id for r in requests} == {"rec-1", "rec-2"}


@pytest.mark.asyncio
async def test_deduplication_via_database():
    """Test concurrent pollers use database for deduplication."""
    # Create room and meeting
    room = Room(
        id="test-room-3", name="Test Room 3", slug="test-room-3", user_id="test-user"
    )
    await rooms_controller.create(room)

    meeting = Meeting(
        id="meeting-789",
        room_name="test-room-3",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="raw-tracks",
    )
    await meetings_controller.create(meeting)

    recording_id = "rec-123"

    # Poller 1
    created1 = await recordings_controller.try_create_with_meeting(
        Recording(
            id=recording_id,
            bucket_name="test-bucket",
            object_key="test-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id="meeting-789",
            status="pending",
            track_keys=["track1.webm", "track2.webm"],
        )
    )
    assert created1 is True  # First wins

    # Poller 2 (concurrent)
    created2 = await recordings_controller.try_create_with_meeting(
        Recording(
            id=recording_id,
            bucket_name="test-bucket",
            object_key="test-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id="meeting-789",
            status="pending",
            track_keys=["track1.webm", "track2.webm"],
        )
    )
    assert created2 is False  # Conflict, skip


@pytest.mark.asyncio
async def test_orphan_logged_once():
    """Test orphan marked once, skipped on re-poll."""
    # First poll
    created1 = await recordings_controller.create_orphan(
        Recording(
            id="orphan-123",
            bucket_name="test-bucket",
            object_key="orphan-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=None,
            status="orphan",
            track_keys=None,
        )
    )
    assert created1 is True

    # Second poll (same orphan discovered again)
    created2 = await recordings_controller.create_orphan(
        Recording(
            id="orphan-123",
            bucket_name="test-bucket",
            object_key="orphan-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=None,
            status="orphan",
            track_keys=None,
        )
    )
    assert created2 is False  # Already exists

    # Verify it exists
    existing = await recordings_controller.get_by_id("orphan-123")
    assert existing is not None
    assert existing.status == "orphan"


@pytest.mark.asyncio
async def test_orphan_constraints():
    """Test orphan invariants are enforced."""
    # Can't create orphan with meeting_id
    with pytest.raises(AssertionError, match="meeting_id must be NULL"):
        await recordings_controller.create_orphan(
            Recording(
                id="bad-orphan-1",
                bucket_name="test",
                object_key="test",
                recorded_at=datetime.now(timezone.utc),
                meeting_id="meeting-123",  # Should be None
                status="orphan",
                track_keys=None,
            )
        )

    # Can't create orphan with wrong status
    with pytest.raises(AssertionError, match="status must be 'orphan'"):
        await recordings_controller.create_orphan(
            Recording(
                id="bad-orphan-2",
                bucket_name="test",
                object_key="test",
                recorded_at=datetime.now(timezone.utc),
                meeting_id=None,
                status="pending",  # Should be "orphan"
                track_keys=None,
            )
        )


@pytest.mark.asyncio
async def test_try_create_with_meeting_constraints():
    """Test try_create_with_meeting enforces constraints."""
    # Create room and meeting
    room = Room(
        id="test-room-4", name="Test Room 4", slug="test-room-4", user_id="test-user"
    )
    await rooms_controller.create(room)

    meeting = Meeting(
        id="meeting-999",
        room_name="test-room-4",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="cloud",
    )
    await meetings_controller.create(meeting)

    # Can't create with orphan status
    with pytest.raises(AssertionError, match="use create_orphan"):
        await recordings_controller.try_create_with_meeting(
            Recording(
                id="bad-rec-1",
                bucket_name="test",
                object_key="test",
                recorded_at=datetime.now(timezone.utc),
                meeting_id="meeting-999",
                status="orphan",  # Should not be orphan
                track_keys=None,
            )
        )

    # Can't create without meeting_id
    with pytest.raises(AssertionError, match="meeting_id required"):
        await recordings_controller.try_create_with_meeting(
            Recording(
                id="bad-rec-2",
                bucket_name="test",
                object_key="test",
                recorded_at=datetime.now(timezone.utc),
                meeting_id=None,  # Should have meeting_id
                status="pending",
                track_keys=None,
            )
        )
