"""Tests for poll_daily_recordings task."""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.dailyco_api.responses import RecordingResponse
from reflector.dailyco_api.webhooks import DailyTrack


# Import the unwrapped async function for testing
# The function is decorated with @shared_task and @asynctask,
# but we need to test the underlying async implementation
def _get_poll_daily_recordings_fn():
    """Get the underlying async function without Celery/asynctask decorators."""
    from reflector.worker import process

    # Access the actual async function before decorators
    fn = process.poll_daily_recordings
    # Get through both decorator layers
    if hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    if hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


@pytest.fixture
def mock_recording_response():
    """Mock Daily.co API recording response with tracks."""
    now = datetime.now(timezone.utc)
    return [
        RecordingResponse(
            id="rec-123",
            room_name="test-room-20251118120000",
            start_ts=int((now - timedelta(hours=1)).timestamp()),
            status="finished",
            max_participants=2,
            duration=3600,
            share_token="share-token-123",
            tracks=[
                DailyTrack(type="audio", s3Key="track1.webm", size=1024),
                DailyTrack(type="audio", s3Key="track2.webm", size=2048),
            ],
        ),
        RecordingResponse(
            id="rec-456",
            room_name="test-room-20251118130000",
            start_ts=int((now - timedelta(hours=2)).timestamp()),
            status="finished",
            max_participants=3,
            duration=7200,
            share_token="share-token-456",
            tracks=[
                DailyTrack(type="audio", s3Key="track1.webm", size=1024),
            ],
        ),
    ]


@pytest.fixture
def mock_meeting():
    """Mock meeting object."""
    from reflector.db.meetings import Meeting

    return Meeting(
        id="meeting-123",
        room_name="test-room-20251118120000",
        room_url="https://daily.co/test-room",
        host_room_url="https://daily.co/test-room",
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(hours=1),
        room_id="room-123",
        platform="daily",
    )


@pytest.mark.asyncio
@patch("reflector.worker.process.settings")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids")
@patch("reflector.worker.process.meetings_controller.get_by_room_name")
@patch("reflector.worker.process.process_multitrack_recording.delay")
async def test_poll_daily_recordings_processes_missing_recordings(
    mock_process_delay,
    mock_get_meeting,
    mock_get_recordings,
    mock_create_client,
    mock_settings,
    mock_recording_response,
    mock_meeting,
):
    """Test that poll_daily_recordings queues processing for recordings not in DB."""
    mock_settings.DAILYCO_STORAGE_AWS_BUCKET_NAME = "test-bucket"

    # Mock Daily.co API client
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_recording_response)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Mock DB controller - no existing recordings
    mock_get_recordings.return_value = []

    # Mock meeting exists for all recordings
    mock_get_meeting.return_value = mock_meeting

    # Execute - call the unwrapped async function
    poll_fn = _get_poll_daily_recordings_fn()
    await poll_fn()

    # Verify Daily.co API was called without time parameters (uses default limit=100)
    assert mock_daily_client.list_recordings.call_count == 1
    call_kwargs = mock_daily_client.list_recordings.call_args.kwargs

    # Should not have time-based parameters (uses cursor-based pagination)
    assert "start_time" not in call_kwargs
    assert "end_time" not in call_kwargs

    # Verify processing was queued for both missing recordings
    assert mock_process_delay.call_count == 2

    # Verify the processing calls have correct parameters
    calls = mock_process_delay.call_args_list
    assert calls[0].kwargs["bucket_name"] == "test-bucket"
    assert calls[0].kwargs["recording_id"] == "rec-123"
    assert calls[0].kwargs["daily_room_name"] == "test-room-20251118120000"
    assert calls[0].kwargs["track_keys"] == ["track1.webm", "track2.webm"]

    assert calls[1].kwargs["bucket_name"] == "test-bucket"
    assert calls[1].kwargs["recording_id"] == "rec-456"
    assert calls[1].kwargs["daily_room_name"] == "test-room-20251118130000"
    assert calls[1].kwargs["track_keys"] == ["track1.webm"]


@pytest.mark.asyncio
@patch("reflector.worker.process.settings")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids")
@patch("reflector.worker.process.meetings_controller.get_by_room_name")
@patch("reflector.worker.process.process_multitrack_recording.delay")
async def test_poll_daily_recordings_skips_recordings_without_meeting(
    mock_process_delay,
    mock_get_meeting,
    mock_get_recordings,
    mock_create_client,
    mock_settings,
    mock_recording_response,
):
    """Test that poll_daily_recordings skips recordings without matching meeting."""
    mock_settings.DAILYCO_STORAGE_AWS_BUCKET_NAME = "test-bucket"

    # Mock Daily.co API client
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_recording_response)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Mock DB controller - no existing recordings
    mock_get_recordings.return_value = []

    # Mock no meeting found
    mock_get_meeting.return_value = None

    # Execute - call the unwrapped async function
    poll_fn = _get_poll_daily_recordings_fn()
    await poll_fn()

    # Verify Daily.co API was called
    assert mock_daily_client.list_recordings.call_count == 1

    # Verify NO processing was queued (no matching meetings)
    assert mock_process_delay.call_count == 0


@pytest.mark.asyncio
@patch("reflector.worker.process.settings")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids")
@patch("reflector.worker.process.process_multitrack_recording.delay")
async def test_poll_daily_recordings_skips_existing_recordings(
    mock_process_delay,
    mock_get_recordings,
    mock_create_client,
    mock_settings,
    mock_recording_response,
):
    """Test that poll_daily_recordings skips recordings already in DB."""
    mock_settings.DAILYCO_STORAGE_AWS_BUCKET_NAME = "test-bucket"

    # Mock Daily.co API client
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_recording_response)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Mock DB controller - all recordings already exist
    from reflector.db.recordings import Recording

    mock_get_recordings.return_value = [
        Recording(
            id="rec-123",
            bucket_name="test-bucket",
            object_key="",
            recorded_at=datetime.now(timezone.utc),
            meeting_id="meeting-1",
        ),
        Recording(
            id="rec-456",
            bucket_name="test-bucket",
            object_key="",
            recorded_at=datetime.now(timezone.utc),
            meeting_id="meeting-1",
        ),
    ]

    # Execute - call the unwrapped async function
    poll_fn = _get_poll_daily_recordings_fn()
    await poll_fn()

    # Verify Daily.co API was called
    assert mock_daily_client.list_recordings.call_count == 1

    # Verify NO processing was queued (all recordings already exist)
    assert mock_process_delay.call_count == 0


@pytest.mark.asyncio
@patch("reflector.worker.process.settings")
@patch("reflector.worker.process.create_platform_client")
async def test_poll_daily_recordings_skips_when_bucket_not_configured(
    mock_create_client,
    mock_settings,
):
    """Test that poll_daily_recordings returns early when bucket is not configured."""
    # No bucket configured
    mock_settings.DAILYCO_STORAGE_AWS_BUCKET_NAME = None

    # Mock should not be called
    mock_daily_client = AsyncMock()
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Execute - call the unwrapped async function
    poll_fn = _get_poll_daily_recordings_fn()
    await poll_fn()

    # Verify API was never called
    mock_daily_client.list_recordings.assert_not_called()
