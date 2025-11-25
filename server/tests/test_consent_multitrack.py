from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.db.meetings import (
    MeetingConsent,
    meeting_consent_controller,
    meetings_controller,
)
from reflector.db.recordings import Recording, recordings_controller
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.pipelines.main_live_pipeline import cleanup_consent


@pytest.mark.asyncio
async def test_consent_cleanup_deletes_multitrack_files():
    room = await rooms_controller.add(
        name="Test Room",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic",
        is_shared=False,
        platform="daily",
    )

    # Create meeting
    meeting = await meetings_controller.create(
        id="test-multitrack-meeting",
        room_name="test-room-20250101120000",
        room_url="https://test.daily.co/test-room",
        host_room_url="https://test.daily.co/test-room",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        room=room,
    )

    track_keys = [
        "recordings/test-room-20250101120000/track-0.webm",
        "recordings/test-room-20250101120000/track-1.webm",
        "recordings/test-room-20250101120000/track-2.webm",
    ]
    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="recordings/test-room-20250101120000",  # Folder path
            recorded_at=datetime.now(timezone.utc),
            meeting_id=meeting.id,
            track_keys=track_keys,
        )
    )

    # Create transcript
    transcript = await transcripts_controller.add(
        name="Test Multitrack Transcript",
        source_kind=SourceKind.ROOM,
        recording_id=recording.id,
        meeting_id=meeting.id,
    )

    # Add consent denial
    await meeting_consent_controller.upsert(
        MeetingConsent(
            meeting_id=meeting.id,
            user_id="test-user",
            consent_given=False,
            consent_timestamp=datetime.now(timezone.utc),
        )
    )

    # Mock get_transcripts_storage (master credentials with bucket override)
    with patch(
        "reflector.pipelines.main_live_pipeline.get_transcripts_storage"
    ) as mock_get_transcripts_storage:
        mock_master_storage = MagicMock()
        mock_master_storage.delete_file = AsyncMock()
        mock_get_transcripts_storage.return_value = mock_master_storage

        await cleanup_consent(transcript_id=transcript.id)

    # Verify master storage was used with bucket override for all track keys
    assert mock_master_storage.delete_file.call_count == 3
    deleted_keys = []
    for call_args in mock_master_storage.delete_file.call_args_list:
        key = call_args[0][0]
        bucket_kwarg = call_args[1].get("bucket")
        deleted_keys.append(key)
        assert bucket_kwarg == "test-bucket"  # Verify bucket override!
    assert set(deleted_keys) == set(track_keys)

    updated_transcript = await transcripts_controller.get_by_id(transcript.id)
    assert updated_transcript.audio_deleted is True


@pytest.mark.asyncio
async def test_consent_cleanup_handles_missing_track_keys():
    room = await rooms_controller.add(
        name="Test Room 2",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic",
        is_shared=False,
        platform="daily",
    )

    # Create meeting
    meeting = await meetings_controller.create(
        id="test-multitrack-meeting-2",
        room_name="test-room-20250101120001",
        room_url="https://test.daily.co/test-room-2",
        host_room_url="https://test.daily.co/test-room-2",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        room=room,
    )

    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="recordings/old-style-recording.mp4",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=meeting.id,
            track_keys=None,
        )
    )

    transcript = await transcripts_controller.add(
        name="Test Old-Style Transcript",
        source_kind=SourceKind.ROOM,
        recording_id=recording.id,
        meeting_id=meeting.id,
    )

    # Add consent denial
    await meeting_consent_controller.upsert(
        MeetingConsent(
            meeting_id=meeting.id,
            user_id="test-user-2",
            consent_given=False,
            consent_timestamp=datetime.now(timezone.utc),
        )
    )

    # Mock get_transcripts_storage (master credentials with bucket override)
    with patch(
        "reflector.pipelines.main_live_pipeline.get_transcripts_storage"
    ) as mock_get_transcripts_storage:
        mock_master_storage = MagicMock()
        mock_master_storage.delete_file = AsyncMock()
        mock_get_transcripts_storage.return_value = mock_master_storage

        await cleanup_consent(transcript_id=transcript.id)

    # Verify master storage was used with bucket override
    assert mock_master_storage.delete_file.call_count == 1
    call_args = mock_master_storage.delete_file.call_args
    assert call_args[0][0] == recording.object_key
    assert call_args[1].get("bucket") == "test-bucket"  # Verify bucket override!


@pytest.mark.asyncio
async def test_consent_cleanup_empty_track_keys_falls_back():
    room = await rooms_controller.add(
        name="Test Room 3",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic",
        is_shared=False,
        platform="daily",
    )

    # Create meeting
    meeting = await meetings_controller.create(
        id="test-multitrack-meeting-3",
        room_name="test-room-20250101120002",
        room_url="https://test.daily.co/test-room-3",
        host_room_url="https://test.daily.co/test-room-3",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        room=room,
    )

    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="recordings/fallback-recording.mp4",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=meeting.id,
            track_keys=[],
        )
    )

    transcript = await transcripts_controller.add(
        name="Test Empty Track Keys Transcript",
        source_kind=SourceKind.ROOM,
        recording_id=recording.id,
        meeting_id=meeting.id,
    )

    # Add consent denial
    await meeting_consent_controller.upsert(
        MeetingConsent(
            meeting_id=meeting.id,
            user_id="test-user-3",
            consent_given=False,
            consent_timestamp=datetime.now(timezone.utc),
        )
    )

    # Mock get_transcripts_storage (master credentials with bucket override)
    with patch(
        "reflector.pipelines.main_live_pipeline.get_transcripts_storage"
    ) as mock_get_transcripts_storage:
        mock_master_storage = MagicMock()
        mock_master_storage.delete_file = AsyncMock()
        mock_get_transcripts_storage.return_value = mock_master_storage

        # Run cleanup
        await cleanup_consent(transcript_id=transcript.id)

    # Verify master storage was used with bucket override
    assert mock_master_storage.delete_file.call_count == 1
    call_args = mock_master_storage.delete_file.call_args
    assert call_args[0][0] == recording.object_key
    assert call_args[1].get("bucket") == "test-bucket"  # Verify bucket override!


@pytest.mark.asyncio
async def test_consent_cleanup_partial_failure_doesnt_mark_deleted():
    room = await rooms_controller.add(
        name="Test Room 4",
        user_id="test-user",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic",
        is_shared=False,
        platform="daily",
    )

    # Create meeting
    meeting = await meetings_controller.create(
        id="test-multitrack-meeting-4",
        room_name="test-room-20250101120003",
        room_url="https://test.daily.co/test-room-4",
        host_room_url="https://test.daily.co/test-room-4",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
        room=room,
    )

    track_keys = [
        "recordings/test-room-20250101120003/track-0.webm",
        "recordings/test-room-20250101120003/track-1.webm",
        "recordings/test-room-20250101120003/track-2.webm",
    ]
    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="recordings/test-room-20250101120003",
            recorded_at=datetime.now(timezone.utc),
            meeting_id=meeting.id,
            track_keys=track_keys,
        )
    )

    # Create transcript
    transcript = await transcripts_controller.add(
        name="Test Partial Failure Transcript",
        source_kind=SourceKind.ROOM,
        recording_id=recording.id,
        meeting_id=meeting.id,
    )

    # Add consent denial
    await meeting_consent_controller.upsert(
        MeetingConsent(
            meeting_id=meeting.id,
            user_id="test-user-4",
            consent_given=False,
            consent_timestamp=datetime.now(timezone.utc),
        )
    )

    # Mock get_transcripts_storage (master credentials with bucket override) with partial failure
    with patch(
        "reflector.pipelines.main_live_pipeline.get_transcripts_storage"
    ) as mock_get_transcripts_storage:
        mock_master_storage = MagicMock()

        call_count = 0

        async def delete_side_effect(key, bucket=None):
            nonlocal call_count
            call_count += 1
            if call_count == 2:
                raise Exception("S3 deletion failed")

        mock_master_storage.delete_file = AsyncMock(side_effect=delete_side_effect)
        mock_get_transcripts_storage.return_value = mock_master_storage

        await cleanup_consent(transcript_id=transcript.id)

    # Verify master storage was called with bucket override
    assert mock_master_storage.delete_file.call_count == 3

    updated_transcript = await transcripts_controller.get_by_id(transcript.id)
    assert (
        updated_transcript.audio_deleted is None
        or updated_transcript.audio_deleted is False
    )
