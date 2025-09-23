from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import insert

from reflector.db.base import MeetingModel, RoomModel
from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import SourceKind, transcripts_controller


@pytest.mark.asyncio
async def test_recording_deleted_with_transcript(db_db_session):
    """Test that a recording is deleted when its associated transcript is deleted."""
    # First create a room and meeting to satisfy foreign key constraints
    room_id = "test-room"
    await db_session.execute(
        insert(RoomModel).values(
            id=room_id,
            name="test-room",
            user_id="test-user",
            created_at=datetime.now(timezone.utc),
            zulip_auto_post=False,
            zulip_stream="",
            zulip_topic="",
            is_locked=False,
            room_mode="normal",
            recording_type="cloud",
            recording_trigger="automatic",
            is_shared=False,
        )
    )

    meeting_id = "test-meeting"
    await db_session.execute(
        insert(MeetingModel).values(
            id=meeting_id,
            room_id=room_id,
            room_name="test-room",
            room_url="https://example.com/room",
            host_room_url="https://example.com/room-host",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc),
            is_active=False,
            num_clients=0,
            is_locked=False,
            room_mode="normal",
            recording_type="cloud",
            recording_trigger="automatic",
        )
    )
    await db_session.commit()

    # Now create a recording
    recording = await recordings_controller.create(
        session,
        meeting_id=meeting_id,
        url="https://example.com/recording.mp4",
        object_key="recordings/test.mp4",
        duration=3600.0,
        created_at=datetime.now(timezone.utc),
    )

    # Create a transcript associated with the recording
    transcript = await transcripts_controller.add(
        session,
        name="Test Transcript",
        source_kind=SourceKind.ROOM,
        recording_id=recording.id,
    )

    # Mock the storage deletion
    with patch("reflector.db.transcripts.get_recordings_storage") as mock_get_storage:
        storage_instance = mock_get_storage.return_value
        storage_instance.delete_file = AsyncMock()

        # Delete the transcript
        await transcripts_controller.remove_by_id(session, transcript.id)

        # Verify that the recording file was deleted from storage
        storage_instance.delete_file.assert_awaited_once_with(recording.object_key)

    # Verify both the recording and transcript are deleted
    assert await recordings_controller.get_by_id(session, recording.id) is None
    assert await transcripts_controller.get_by_id(session, transcript.id) is None
