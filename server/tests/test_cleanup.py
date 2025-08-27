from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

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
async def test_cleanup_deletes_associated_meeting_and_recording():
    """Test that meetings and recordings associated with old transcripts are deleted."""
    from reflector.db import get_database
    from reflector.db.meetings import meetings
    from reflector.db.transcripts import transcripts
    
    old_date = datetime.now(timezone.utc) - timedelta(days=8)
    
    # Create a meeting
    meeting_id = "test-meeting-for-transcript"
    await get_database().execute(
        meetings.insert().values(
            id=meeting_id,
            room_name="Meeting with Transcript",
            room_url="https://example.com/meeting",
            host_room_url="https://example.com/meeting-host",
            start_date=old_date,
            end_date=old_date + timedelta(hours=1),
            user_id=None,
            room_id=None,
        )
    )
    
    # Create a recording
    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="test-recording.mp4",
            recorded_at=old_date,
        )
    )
    
    # Create an old transcript with both meeting and recording
    old_transcript = await transcripts_controller.add(
        name="Old Transcript with Meeting and Recording",
        source_kind=SourceKind.ROOM,
        user_id=None,
        meeting_id=meeting_id,
        recording_id=recording.id,
    )
    
    # Update created_at to be old
    await get_database().execute(
        transcripts.update()
        .where(transcripts.c.id == old_transcript.id)
        .values(created_at=old_date)
    )
    
    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7
        
        # Mock storage deletion
        with patch("reflector.db.transcripts.get_transcripts_storage") as mock_storage:
            mock_storage.return_value.delete_file = AsyncMock()
            with patch("reflector.worker.cleanup.get_recordings_storage") as mock_rec_storage:
                mock_rec_storage.return_value.delete_file = AsyncMock()
                
                result = await _cleanup_old_public_data()
    
    # Check results
    assert result["transcripts_deleted"] == 1
    assert result["meetings_deleted"] == 1
    assert result["recordings_deleted"] == 1
    assert result["errors"] == []
    
    # Verify transcript was deleted
    assert await transcripts_controller.get_by_id(old_transcript.id) is None
    
    # Verify meeting was deleted
    query = meetings.select().where(meetings.c.id == meeting_id)
    meeting_result = await get_database().fetch_one(query)
    assert meeting_result is None
    
    # Verify recording was deleted
    assert await recordings_controller.get_by_id(recording.id) is None


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
async def test_meeting_consent_cascade_delete():
    """Test that meeting_consent records are automatically deleted when meeting is deleted."""
    from reflector.db import get_database
    from reflector.db.meetings import (
        meeting_consent,
        meeting_consent_controller,
        meetings,
    )

    # Create a meeting
    meeting_id = "test-cascade-meeting"
    await get_database().execute(
        meetings.insert().values(
            id=meeting_id,
            room_name="Test Meeting for CASCADE",
            room_url="https://example.com/cascade-test",
            host_room_url="https://example.com/cascade-test-host",
            start_date=datetime.now(timezone.utc),
            end_date=datetime.now(timezone.utc) + timedelta(hours=1),
            user_id="test-user",
            room_id=None,
        )
    )

    # Create consent records for this meeting
    consent1_id = "consent-1"
    consent2_id = "consent-2"

    await get_database().execute(
        meeting_consent.insert().values(
            id=consent1_id,
            meeting_id=meeting_id,
            user_id="user1",
            consent_given=True,
            consent_timestamp=datetime.now(timezone.utc),
        )
    )

    await get_database().execute(
        meeting_consent.insert().values(
            id=consent2_id,
            meeting_id=meeting_id,
            user_id="user2",
            consent_given=False,
            consent_timestamp=datetime.now(timezone.utc),
        )
    )

    # Verify consent records exist
    consents = await meeting_consent_controller.get_by_meeting_id(meeting_id)
    assert len(consents) == 2

    # Delete the meeting
    await get_database().execute(meetings.delete().where(meetings.c.id == meeting_id))

    # Verify meeting is deleted
    query = meetings.select().where(meetings.c.id == meeting_id)
    result = await get_database().fetch_one(query)
    assert result is None

    # Verify consent records are automatically deleted (CASCADE DELETE)
    consents_after = await meeting_consent_controller.get_by_meeting_id(meeting_id)
    assert len(consents_after) == 0
