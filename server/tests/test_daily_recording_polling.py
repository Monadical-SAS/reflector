"""Tests for Daily.co recording polling functionality.

TDD tests for Task 3.1: Recording Polling
- Query last 2 hours of recordings from Daily.co API
- Compare with DB to find missing recordings
- Process only recordings not already in DB
- Use existing worker lock for deduplication
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.dailyco_api.responses import RecordingResponse
from reflector.db.recordings import Recording
from reflector.worker.process import poll_daily_recordings


@pytest.fixture
def mock_daily_recordings():
    """Mock Daily.co API response with 3 recordings."""
    now = datetime.now(timezone.utc)
    return [
        RecordingResponse(
            id="daily-rec-1",
            room_name="room1-20251118120000",
            start_ts=int((now - timedelta(hours=1)).timestamp()),
            duration=600,
            status="finished",
            max_participants=2,
        ),
        RecordingResponse(
            id="daily-rec-2",
            room_name="room2-20251118120000",
            start_ts=int((now - timedelta(minutes=30)).timestamp()),
            duration=300,
            status="finished",
            max_participants=1,
        ),
        RecordingResponse(
            id="daily-rec-3",
            room_name="room3-20251118120000",
            start_ts=int((now - timedelta(minutes=15)).timestamp()),
            duration=150,
            status="finished",
            max_participants=3,
        ),
    ]


@pytest.mark.asyncio
@patch(
    "reflector.worker.process.settings.DAILYCO_STORAGE_AWS_BUCKET_NAME", "test-bucket"
)
@patch("reflector.worker.process.get_dailyco_storage")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids_batch")
@patch("reflector.worker.process.process_multitrack_recording")
async def test_poll_daily_recordings_processes_missing_only(
    mock_process_task,
    mock_get_recordings_batch,
    mock_create_client,
    mock_get_storage,
    mock_daily_recordings,
):
    """Test that polling processes only recordings not already in DB."""
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_daily_recordings)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Mock storage to return tracks for each room
    mock_storage = AsyncMock()
    mock_storage.list_objects = AsyncMock(
        side_effect=lambda prefix: [
            f"{prefix}track-0-cam-audio.webm",
            f"{prefix}track-1-cam-audio.webm",
        ]
    )
    mock_get_storage.return_value = mock_storage

    mock_get_recordings_batch.return_value = [
        Recording(
            id="daily-rec-1",
            bucket_name="test-bucket",
            object_key="monadical/room1/track.webm",
            recorded_at=datetime.now(timezone.utc),
            status="completed",
        )
    ]

    mock_delay = MagicMock()
    mock_process_task.delay = mock_delay

    await poll_daily_recordings()

    assert mock_daily_client.list_recordings.call_count == 1
    call_kwargs = mock_daily_client.list_recordings.call_args.kwargs
    assert "start_time" in call_kwargs
    assert "end_time" in call_kwargs

    assert mock_delay.call_count == 2
    # Verify track_keys are populated
    for call in mock_delay.call_args_list:
        track_keys = call.kwargs["track_keys"]
        assert len(track_keys) == 2
        assert all("cam-audio" in key for key in track_keys)


@pytest.mark.asyncio
@patch(
    "reflector.worker.process.settings.DAILYCO_STORAGE_AWS_BUCKET_NAME", "test-bucket"
)
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids_batch")
@patch("reflector.worker.process.process_multitrack_recording")
async def test_poll_daily_recordings_skips_all_if_in_db(
    mock_process_task,
    mock_get_recordings_batch,
    mock_create_client,
    mock_daily_recordings,
):
    """Test that polling skips recordings already in DB."""
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_daily_recordings)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    mock_get_recordings_batch.return_value = [
        Recording(
            id=rec.id,
            bucket_name="test-bucket",
            object_key=f"monadical/{rec.room_name}/track.webm",
            recorded_at=datetime.fromtimestamp(rec.start_ts, tz=timezone.utc),
            status="completed",
        )
        for rec in mock_daily_recordings
    ]

    mock_delay = MagicMock()
    mock_process_task.delay = mock_delay

    await poll_daily_recordings()

    assert mock_delay.call_count == 0


@pytest.mark.asyncio
@patch("reflector.worker.process.settings.DAILYCO_STORAGE_AWS_BUCKET_NAME", None)
@patch("reflector.worker.process.create_platform_client")
async def test_poll_daily_recordings_skip_if_no_bucket_config(mock_create_client):
    """Test that polling exits early if bucket not configured."""
    mock_daily_client = AsyncMock()
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    await poll_daily_recordings()

    assert mock_daily_client.list_recordings.call_count == 0


@pytest.mark.asyncio
@patch(
    "reflector.worker.process.settings.DAILYCO_STORAGE_AWS_BUCKET_NAME", "test-bucket"
)
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids_batch")
@patch("reflector.worker.process.process_multitrack_recording")
async def test_poll_daily_recordings_handles_empty_api_response(
    mock_process_task, mock_get_recordings_batch, mock_create_client
):
    """Test that polling handles empty API response gracefully."""
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=[])
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    mock_delay = MagicMock()
    mock_process_task.delay = mock_delay

    await poll_daily_recordings()

    assert mock_delay.call_count == 0
    assert mock_get_recordings_batch.call_count == 0


@pytest.mark.asyncio
@patch(
    "reflector.worker.process.settings.DAILYCO_STORAGE_AWS_BUCKET_NAME", "test-bucket"
)
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids_batch")
@patch("reflector.worker.process.process_multitrack_recording")
async def test_poll_daily_recordings_uses_correct_time_window(
    mock_process_task,
    mock_get_recordings_batch,
    mock_create_client,
    mock_daily_recordings,
):
    """Test that polling queries last 2 hours of recordings."""
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_daily_recordings)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    mock_get_recordings_batch.return_value = []
    mock_delay = MagicMock()
    mock_process_task.delay = mock_delay

    before = datetime.now(timezone.utc)
    await poll_daily_recordings()
    after = datetime.now(timezone.utc)

    call_kwargs = mock_daily_client.list_recordings.call_args.kwargs
    start_time = call_kwargs["start_time"]
    end_time = call_kwargs["end_time"]

    expected_start = int((before - timedelta(hours=2)).timestamp())
    expected_end = int(after.timestamp())

    assert expected_start - 5 <= start_time <= expected_start + 5
    assert expected_end - 5 <= end_time <= expected_end + 5


@pytest.mark.asyncio
@patch(
    "reflector.worker.process.settings.DAILYCO_STORAGE_AWS_BUCKET_NAME", "test-bucket"
)
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.process_multitrack_recording")
async def test_poll_daily_recordings_handles_api_error(
    mock_process_task, mock_create_client
):
    """Test that API failures are logged and don't crash polling."""
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(side_effect=Exception("API timeout"))
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    mock_delay = MagicMock()
    mock_process_task.delay = mock_delay

    await poll_daily_recordings()

    assert mock_delay.call_count == 0
