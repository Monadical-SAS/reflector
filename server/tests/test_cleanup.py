from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.meetings import meetings_controller
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.worker.cleanup import _cleanup_old_public_data


@pytest.mark.asyncio
async def test_cleanup_old_public_data_skips_when_not_public():
    """Test that cleanup is skipped when PUBLIC_MODE is False."""
    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = False

        result = await _cleanup_old_public_data()

        # Should return early without doing anything
        assert result is None


@pytest.mark.asyncio
async def test_cleanup_old_public_data_deletes_old_anonymous_transcripts():
    """Test that old anonymous transcripts are deleted."""
    # Create old and new anonymous transcripts
    old_date = datetime.now(timezone.utc) - timedelta(days=8)
    new_date = datetime.now(timezone.utc) - timedelta(days=2)

    # Create old anonymous transcript (should be deleted)
    old_transcript = await transcripts_controller.add(
        name="Old Anonymous Transcript",
        source_kind=SourceKind.FILE,
        user_id=None,  # Anonymous
    )
    # Manually update created_at to be old
    from reflector.db import get_database
    from reflector.db.transcripts import transcripts

    await get_database().execute(
        transcripts.update()
        .where(transcripts.c.id == old_transcript.id)
        .values(created_at=old_date)
    )

    # Create new anonymous transcript (should NOT be deleted)
    new_transcript = await transcripts_controller.add(
        name="New Anonymous Transcript",
        source_kind=SourceKind.FILE,
        user_id=None,  # Anonymous
    )

    # Create old transcript with user (should NOT be deleted)
    old_user_transcript = await transcripts_controller.add(
        name="Old User Transcript",
        source_kind=SourceKind.FILE,
        user_id="user123",
    )
    await get_database().execute(
        transcripts.update()
        .where(transcripts.c.id == old_user_transcript.id)
        .values(created_at=old_date)
    )

    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        # Mock the storage deletion
        with patch("reflector.db.transcripts.get_transcripts_storage") as mock_storage:
            mock_storage.return_value.delete_file = AsyncMock()

            result = await _cleanup_old_public_data()

    # Check results
    assert result["transcripts_deleted"] == 1
    assert result["errors"] == []

    # Verify old anonymous transcript was deleted
    assert await transcripts_controller.get_by_id(old_transcript.id) is None

    # Verify new anonymous transcript still exists
    assert await transcripts_controller.get_by_id(new_transcript.id) is not None

    # Verify user transcript still exists
    assert await transcripts_controller.get_by_id(old_user_transcript.id) is not None


@pytest.mark.asyncio
async def test_cleanup_old_public_data_deletes_old_meetings():
    """Test that old anonymous meetings are deleted."""
    from reflector.db import get_database
    from reflector.db.meetings import meetings

    old_date = datetime.now(timezone.utc) - timedelta(days=8)
    new_date = datetime.now(timezone.utc) - timedelta(days=2)

    # Create old anonymous meeting directly (should be deleted)
    old_meeting_id = "old-meeting-id"
    await get_database().execute(
        meetings.insert().values(
            id=old_meeting_id,
            room_name="Old Meeting",
            room_url="https://example.com/old",
            host_room_url="https://example.com/old-host",
            start_date=old_date,
            end_date=old_date + timedelta(hours=1),
            user_id=None,  # Anonymous
            room_id=None,
        )
    )

    # Create new anonymous meeting directly (should NOT be deleted)
    new_meeting_id = "new-meeting-id"
    await get_database().execute(
        meetings.insert().values(
            id=new_meeting_id,
            room_name="New Meeting",
            room_url="https://example.com/new",
            host_room_url="https://example.com/new-host",
            start_date=new_date,
            end_date=new_date + timedelta(hours=1),
            user_id=None,  # Anonymous
            room_id=None,
        )
    )

    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        result = await _cleanup_old_public_data()

    # Check results
    assert result["meetings_deleted"] == 1
    assert result["errors"] == []

    # Verify old meeting was deleted
    query = meetings.select().where(meetings.c.id == old_meeting_id)
    old_meeting_result = await get_database().fetch_one(query)
    assert old_meeting_result is None

    # Verify new meeting still exists
    query = meetings.select().where(meetings.c.id == new_meeting_id)
    new_meeting_result = await get_database().fetch_one(query)
    assert new_meeting_result is not None


@pytest.mark.asyncio
async def test_cleanup_handles_errors_gracefully():
    """Test that cleanup continues even when individual deletions fail."""
    old_date = datetime.now(timezone.utc) - timedelta(days=8)

    # Create multiple old transcripts
    transcript1 = await transcripts_controller.add(
        name="Transcript 1",
        source_kind=SourceKind.FILE,
        user_id=None,
    )
    transcript2 = await transcripts_controller.add(
        name="Transcript 2",
        source_kind=SourceKind.FILE,
        user_id=None,
    )

    # Update created_at to be old
    from reflector.db import get_database
    from reflector.db.transcripts import transcripts

    for t_id in [transcript1.id, transcript2.id]:
        await get_database().execute(
            transcripts.update()
            .where(transcripts.c.id == t_id)
            .values(created_at=old_date)
        )

    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        # Mock remove_by_id to fail for the first transcript
        original_remove = transcripts_controller.remove_by_id
        call_count = 0

        async def mock_remove_by_id(transcript_id, user_id=None):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated deletion error")
            return await original_remove(transcript_id, user_id)

        with patch.object(
            transcripts_controller, "remove_by_id", side_effect=mock_remove_by_id
        ):
            result = await _cleanup_old_public_data()

    # Should have one successful deletion and one error
    assert result["transcripts_deleted"] == 1
    assert len(result["errors"]) == 1
    assert "Failed to delete transcript" in result["errors"][0]


@pytest.mark.asyncio
async def test_cleanup_deletes_orphaned_recordings():
    """Test that orphaned recordings are deleted."""
    old_date = datetime.now(timezone.utc) - timedelta(days=8)

    # Create an orphaned recording (no transcript references it)
    orphaned_recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="orphaned.mp4",
            recorded_at=old_date,
        )
    )

    # Create a recording with a transcript (should NOT be deleted)
    referenced_recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="referenced.mp4",
            recorded_at=old_date,
        )
    )

    # Create transcript that references the second recording
    transcript = await transcripts_controller.add(
        name="Transcript with Recording",
        source_kind=SourceKind.ROOM,
        recording_id=referenced_recording.id,
    )

    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        result = await _cleanup_old_public_data()

    # Check results
    assert result["recordings_deleted"] == 1
    assert result["errors"] == []

    # Verify orphaned recording was deleted
    assert await recordings_controller.get_by_id(orphaned_recording.id) is None

    # Verify referenced recording still exists
    assert await recordings_controller.get_by_id(referenced_recording.id) is not None
