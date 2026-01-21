"""
Integration tests for recording request flow.

These tests verify the end-to-end flow of:
1. Starting a recording (creates request)
2. Webhook/polling discovering recording (matches via request)
3. Recording processing (uses existing meeting_id)
"""

from datetime import datetime, timezone
from uuid import UUID, uuid4

import pytest

from reflector.db.daily_recording_requests import (
    DailyRecordingRequest,
    daily_recording_requests_controller,
)
from reflector.db.meetings import Meeting, meetings_controller
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.rooms import Room, rooms_controller


@pytest.mark.asyncio
async def test_recording_request_flow_cloud(client):
    """Test full cloud recording flow: start -> webhook -> match"""
    # Create room and meeting
    room = Room(id="test-room", name="Test Room", slug="test-room", user_id="test-user")
    await rooms_controller.create(room)

    meeting_id = f"meeting-{uuid4()}"
    meeting = Meeting(
        id=meeting_id,
        room_name="test-room",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="cloud",
    )
    await meetings_controller.create(meeting)

    # Simulate recording start (what endpoint does)
    recording_id = "rec-cloud-123"
    instance_id = UUID("a1b2c3d4-e5f6-7890-abcd-ef1234567890")

    request = DailyRecordingRequest(
        recording_id=recording_id,
        meeting_id=meeting_id,
        instance_id=instance_id,
        type="cloud",
        requested_at=datetime.now(timezone.utc),
    )
    await daily_recording_requests_controller.create(request)

    # Verify request exists
    match = await daily_recording_requests_controller.find_by_recording_id(recording_id)
    assert match is not None
    assert match[0] == meeting_id
    assert match[1] == "cloud"

    # Simulate webhook/polling storing cloud recording
    success = await meetings_controller.set_cloud_recording_if_missing(
        meeting_id=meeting_id,
        s3_key="s3://bucket/recording.mp4",
        duration=120,
    )
    assert success is True

    # Verify meeting updated
    updated_meeting = await meetings_controller.get_by_id(meeting_id)
    assert updated_meeting.daily_composed_video_s3_key == "s3://bucket/recording.mp4"
    assert updated_meeting.daily_composed_video_duration == 120


@pytest.mark.asyncio
async def test_recording_request_flow_raw_tracks(client):
    """Test full raw-tracks recording flow: start -> webhook/polling -> process"""
    # Create room and meeting
    room = Room(
        id="test-room-2",
        name="Test Room 2",
        slug="test-room-2",
        user_id="test-user",
    )
    await rooms_controller.create(room)

    meeting_id = f"meeting-{uuid4()}"
    meeting = Meeting(
        id=meeting_id,
        room_name="test-room-2",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="raw-tracks",
    )
    await meetings_controller.create(meeting)

    # Simulate recording start
    recording_id = "rec-raw-456"
    instance_id = UUID("b1c2d3e4-f5a6-7890-abcd-ef1234567890")

    request = DailyRecordingRequest(
        recording_id=recording_id,
        meeting_id=meeting_id,
        instance_id=instance_id,
        type="raw-tracks",
        requested_at=datetime.now(timezone.utc),
    )
    await daily_recording_requests_controller.create(request)

    # Simulate webhook/polling discovering recording
    match = await daily_recording_requests_controller.find_by_recording_id(recording_id)
    assert match is not None
    found_meeting_id, recording_type = match
    assert found_meeting_id == meeting_id
    assert recording_type == "raw-tracks"

    # Create recording (what webhook/polling does)
    created = await recordings_controller.try_create_with_meeting(
        Recording(
            id=recording_id,
            bucket_name="test-bucket",
            object_key="recordings/20260120/",
            recorded_at=datetime.now(timezone.utc),
            track_keys=["track1.webm", "track2.webm"],
            meeting_id=meeting_id,
            status="pending",
        )
    )
    assert created is True

    # Verify recording exists with meeting_id
    recording = await recordings_controller.get_by_id(recording_id)
    assert recording is not None
    assert recording.meeting_id == meeting_id
    assert recording.status == "pending"
    assert len(recording.track_keys) == 2


@pytest.mark.asyncio
async def test_stop_restart_creates_multiple_requests(client):
    """Test stop/restart creates multiple request rows with same instance_id"""
    # Create room and meeting
    room = Room(
        id="test-room-3",
        name="Test Room 3",
        slug="test-room-3",
        user_id="test-user",
    )
    await rooms_controller.create(room)

    meeting_id = f"meeting-{uuid4()}"
    meeting = Meeting(
        id=meeting_id,
        room_name="test-room-3",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="cloud",
    )
    await meetings_controller.create(meeting)

    instance_id = UUID("c1d2e3f4-a5b6-7890-abcd-ef1234567890")

    # First recording
    await daily_recording_requests_controller.create(
        DailyRecordingRequest(
            recording_id="rec-first",
            meeting_id=meeting_id,
            instance_id=instance_id,
            type="cloud",
            requested_at=datetime.now(timezone.utc),
        )
    )

    # Stop, then restart (new recording_id, same instance_id)
    await daily_recording_requests_controller.create(
        DailyRecordingRequest(
            recording_id="rec-second",  # DIFFERENT
            meeting_id=meeting_id,
            instance_id=instance_id,  # SAME
            type="cloud",
            requested_at=datetime.now(timezone.utc),
        )
    )

    # Both exist
    requests = await daily_recording_requests_controller.get_by_meeting_id(meeting_id)
    assert len(requests) == 2
    assert {r.recording_id for r in requests} == {"rec-first", "rec-second"}
    assert all(r.instance_id == instance_id for r in requests)


@pytest.mark.asyncio
async def test_orphan_recording_no_request(client):
    """Test orphan recording (no request found)"""
    # Simulate polling discovering recording with no request
    recording_id = "rec-orphan"

    match = await daily_recording_requests_controller.find_by_recording_id(recording_id)
    assert match is None  # No request

    # Mark as orphan
    created = await recordings_controller.create_orphan(
        Recording(
            id=recording_id,
            bucket_name="test-bucket",
            object_key="orphan-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=None,
            status="orphan",
            track_keys=None,
        )
    )
    assert created is True

    # Verify orphan exists
    recording = await recordings_controller.get_by_id(recording_id)
    assert recording is not None
    assert recording.status == "orphan"
    assert recording.meeting_id is None

    # Second poll - already exists
    created_again = await recordings_controller.create_orphan(
        Recording(
            id=recording_id,
            bucket_name="test-bucket",
            object_key="orphan-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=None,
            status="orphan",
            track_keys=None,
        )
    )
    assert created_again is False  # Already exists


@pytest.mark.asyncio
async def test_concurrent_polling_deduplication(client):
    """Test concurrent pollers only queue once"""
    # Create room and meeting
    room = Room(
        id="test-room-4",
        name="Test Room 4",
        slug="test-room-4",
        user_id="test-user",
    )
    await rooms_controller.create(room)

    meeting_id = f"meeting-{uuid4()}"
    meeting = Meeting(
        id=meeting_id,
        room_name="test-room-4",
        start_date=datetime.now(timezone.utc),
        end_date=None,
        recording_type="raw-tracks",
    )
    await meetings_controller.create(meeting)

    # Create request
    recording_id = "rec-concurrent"
    await daily_recording_requests_controller.create(
        DailyRecordingRequest(
            recording_id=recording_id,
            meeting_id=meeting_id,
            instance_id=UUID("d1e2f3a4-b5c6-7890-abcd-ef1234567890"),
            type="raw-tracks",
            requested_at=datetime.now(timezone.utc),
        )
    )

    # Poller 1
    created1 = await recordings_controller.try_create_with_meeting(
        Recording(
            id=recording_id,
            bucket_name="test-bucket",
            object_key="test-key",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=meeting_id,
            status="pending",
            track_keys=["track1.webm"],
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
            meeting_id=meeting_id,
            status="pending",
            track_keys=["track1.webm"],
        )
    )
    assert created2 is False  # Conflict, skip

    # Only one recording exists
    recording = await recordings_controller.get_by_id(recording_id)
    assert recording is not None
    assert recording.meeting_id == meeting_id
