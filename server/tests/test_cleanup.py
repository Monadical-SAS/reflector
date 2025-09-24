from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import delete, insert, select, update

from reflector.db.base import (
    MeetingConsentModel,
    MeetingModel,
    RecordingModel,
    TranscriptModel,
)
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.worker.cleanup import cleanup_old_public_data


@pytest.mark.asyncio
async def test_cleanup_old_public_data_skips_when_not_public(db_session):
    """Test that cleanup is skipped when PUBLIC_MODE is False."""
    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = False

        result = await cleanup_old_public_data(db_session)

        # Should return early without doing anything
        assert result is None


@pytest.mark.asyncio
async def test_cleanup_old_public_data_deletes_old_anonymous_transcripts(db_session):
    """Test that old anonymous transcripts are deleted."""
    # Create old and new anonymous transcripts
    old_date = datetime.now(timezone.utc) - timedelta(days=8)
    new_date = datetime.now(timezone.utc) - timedelta(days=2)

    # Create old anonymous transcript (should be deleted)
    old_transcript = await transcripts_controller.add(
        db_session,
        name="Old Anonymous Transcript",
        source_kind=SourceKind.FILE,
        user_id=None,  # Anonymous
    )

    # Manually update created_at to be old
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == old_transcript.id)
        .values(created_at=old_date)
    )
    await db_session.commit()

    # Create new anonymous transcript (should NOT be deleted)
    new_transcript = await transcripts_controller.add(
        db_session,
        name="New Anonymous Transcript",
        source_kind=SourceKind.FILE,
        user_id=None,  # Anonymous
    )

    # Create old transcript with user (should NOT be deleted)
    old_user_transcript = await transcripts_controller.add(
        db_session,
        name="Old User Transcript",
        source_kind=SourceKind.FILE,
        user_id="user-123",
    )
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == old_user_transcript.id)
        .values(created_at=old_date)
    )
    await db_session.commit()

    # Mock settings for public mode
    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        # Mock delete_single_transcript to track what gets deleted
        with patch("reflector.worker.cleanup.delete_single_transcript") as mock_delete:
            mock_delete.return_value = None

            # Run cleanup with test session
            await cleanup_old_public_data(db_session)

            # Verify only old anonymous transcript was deleted
            assert mock_delete.call_count == 1
            # The function is called with session_factory, transcript_data dict, and stats dict
            call_args = mock_delete.call_args[0]
            transcript_data = call_args[1]
            assert transcript_data["id"] == old_transcript.id


@pytest.mark.asyncio
async def test_cleanup_deletes_associated_meeting_and_recording(db_session):
    """Test that cleanup deletes associated meetings and recordings."""
    old_date = datetime.now(timezone.utc) - timedelta(days=8)

    # Create an old transcript with both meeting and recording
    old_transcript = await transcripts_controller.add(
        db_session,
        name="Old Transcript with Meeting and Recording",
        source_kind=SourceKind.FILE,
        user_id=None,
    )
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == old_transcript.id)
        .values(created_at=old_date)
    )
    await db_session.commit()

    # Create associated meeting directly
    meeting_id = "test-meeting-id"
    await db_session.execute(
        insert(MeetingModel).values(
            id=meeting_id,
            room_id=None,
            room_name="test-room",
            room_url="https://example.com/room",
            host_room_url="https://example.com/room-host",
            start_date=old_date,
            end_date=old_date + timedelta(hours=1),
            is_active=False,
            num_clients=0,
            is_locked=False,
            room_mode="normal",
            recording_type="cloud",
            recording_trigger="automatic",
        )
    )

    # Create associated recording directly
    recording_id = "test-recording-id"
    await db_session.execute(
        insert(RecordingModel).values(
            id=recording_id,
            meeting_id=meeting_id,
            url="https://example.com/recording.mp4",
            object_key="recordings/test.mp4",
            duration=3600.0,
            created_at=old_date,
        )
    )
    await db_session.commit()

    # Update transcript with meeting_id and recording_id
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == old_transcript.id)
        .values(meeting_id=meeting_id, recording_id=recording_id)
    )
    await db_session.commit()

    # Mock settings
    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        # Mock storage deletion
        with patch("reflector.worker.cleanup.get_recordings_storage") as mock_storage:
            mock_storage.return_value.delete_file = AsyncMock()

            # Run cleanup with test session
            await cleanup_old_public_data(db_session)

            # Verify transcript was deleted
            result = await db_session.execute(
                select(TranscriptModel).where(TranscriptModel.id == old_transcript.id)
            )
            transcript = result.scalar_one_or_none()
            assert transcript is None

            # Verify meeting was deleted
            result = await db_session.execute(
                select(MeetingModel).where(MeetingModel.id == meeting_id)
            )
            meeting = result.scalar_one_or_none()
            assert meeting is None

            # Verify recording was deleted
            result = await db_session.execute(
                select(RecordingModel).where(RecordingModel.id == recording_id)
            )
            recording = result.scalar_one_or_none()
            assert recording is None


@pytest.mark.asyncio
async def test_cleanup_handles_errors_gracefully(db_session):
    """Test that cleanup continues even if individual deletions fail."""
    old_date = datetime.now(timezone.utc) - timedelta(days=8)

    # Create multiple old transcripts
    transcript1 = await transcripts_controller.add(
        db_session,
        name="Transcript 1",
        source_kind=SourceKind.FILE,
        user_id=None,
    )
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == transcript1.id)
        .values(created_at=old_date)
    )

    transcript2 = await transcripts_controller.add(
        db_session,
        name="Transcript 2",
        source_kind=SourceKind.FILE,
        user_id=None,
    )
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == transcript2.id)
        .values(created_at=old_date)
    )
    await db_session.commit()

    with patch("reflector.worker.cleanup.settings") as mock_settings:
        mock_settings.PUBLIC_MODE = True
        mock_settings.PUBLIC_DATA_RETENTION_DAYS = 7

        # Mock delete_single_transcript to fail on first call but succeed on second
        with patch("reflector.worker.cleanup.delete_single_transcript") as mock_delete:
            mock_delete.side_effect = [Exception("Delete failed"), None]

            # Run cleanup with test session - should not raise exception
            await cleanup_old_public_data(db_session)

            # Both transcripts should have been attempted to delete
            assert mock_delete.call_count == 2


@pytest.mark.asyncio
async def test_meeting_consent_cascade_delete(db_session):
    """Test that meeting_consent entries are cascade deleted with meetings."""
    old_date = datetime.now(timezone.utc) - timedelta(days=8)

    # Create an old transcript
    transcript = await transcripts_controller.add(
        db_session,
        name="Transcript with Meeting",
        source_kind=SourceKind.FILE,
        user_id=None,
    )
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == transcript.id)
        .values(created_at=old_date)
    )
    await db_session.commit()

    # Create a meeting directly
    meeting_id = "test-meeting-consent"
    await db_session.execute(
        insert(MeetingModel).values(
            id=meeting_id,
            room_id=None,
            room_name="test-room",
            room_url="https://example.com/room",
            host_room_url="https://example.com/room-host",
            start_date=old_date,
            end_date=old_date + timedelta(hours=1),
            is_active=False,
            num_clients=0,
            is_locked=False,
            room_mode="normal",
            recording_type="cloud",
            recording_trigger="automatic",
        )
    )
    await db_session.commit()

    # Update transcript with meeting_id
    await db_session.execute(
        update(TranscriptModel)
        .where(TranscriptModel.id == transcript.id)
        .values(meeting_id=meeting_id)
    )
    await db_session.commit()

    # Create meeting_consent entries
    await db_session.execute(
        insert(MeetingConsentModel).values(
            id="consent-1",
            meeting_id=meeting_id,
            user_id="user-1",
            consent_given=True,
            consent_timestamp=old_date,
        )
    )
    await db_session.execute(
        insert(MeetingConsentModel).values(
            id="consent-2",
            meeting_id=meeting_id,
            user_id="user-2",
            consent_given=True,
            consent_timestamp=old_date,
        )
    )
    await db_session.commit()

    # Verify consent entries exist
    result = await db_session.execute(
        select(MeetingConsentModel).where(MeetingConsentModel.meeting_id == meeting_id)
    )
    consents = result.scalars().all()
    assert len(consents) == 2

    # Delete the transcript and meeting
    await db_session.execute(
        delete(TranscriptModel).where(TranscriptModel.id == transcript.id)
    )
    await db_session.execute(delete(MeetingModel).where(MeetingModel.id == meeting_id))
    await db_session.commit()

    # Verify consent entries were cascade deleted
    result = await db_session.execute(
        select(MeetingConsentModel).where(MeetingConsentModel.meeting_id == meeting_id)
    )
    consents = result.scalars().all()
    assert len(consents) == 0
