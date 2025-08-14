from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.recordings import Recording, recordings_controller
from reflector.db.transcripts import SourceKind, transcripts_controller


@pytest.mark.asyncio
async def test_recording_deleted_with_transcript():
    recording = await recordings_controller.create(
        Recording(
            bucket_name="test-bucket",
            object_key="recording.mp4",
            recorded_at=datetime.now(timezone.utc),
        )
    )
    transcript = await transcripts_controller.add(
        name="Test Transcript",
        source_kind=SourceKind.ROOM,
        recording_id=recording.id,
    )

    with patch("reflector.db.transcripts.get_transcripts_storage") as mock_get_storage:
        storage_instance = mock_get_storage.return_value
        storage_instance.delete_file = AsyncMock()

        await transcripts_controller.remove_by_id(transcript.id)

        storage_instance.delete_file.assert_awaited_once_with(recording.object_key)

    assert await recordings_controller.get_by_id(recording.id) is None
    assert await transcripts_controller.get_by_id(transcript.id) is None
