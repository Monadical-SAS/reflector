"""Tests for poll_daily_recordings configurable lookback window."""

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


@pytest.mark.asyncio
@patch("reflector.worker.process.settings")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids")
@patch("reflector.worker.process.process_multitrack_recording.delay")
async def test_poll_daily_recordings_uses_configurable_lookback_window(
    mock_process_delay,
    mock_get_recordings,
    mock_create_client,
    mock_settings,
    mock_recording_response,
):
    """Test that poll_daily_recordings uses DAILY_RECORDING_POLL_LOOKBACK_HOURS setting."""
    # Configure custom lookback window
    mock_settings.DAILYCO_STORAGE_AWS_BUCKET_NAME = "test-bucket"
    mock_settings.DAILY_RECORDING_POLL_LOOKBACK_HOURS = 48

    # Mock Daily.co API client
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_recording_response)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Mock DB controller - no existing recordings
    mock_get_recordings.return_value = []

    # Execute - call the unwrapped async function
    poll_fn = _get_poll_daily_recordings_fn()
    await poll_fn()

    # Verify Daily.co API was called with correct time range
    assert mock_daily_client.list_recordings.call_count == 1
    call_kwargs = mock_daily_client.list_recordings.call_args.kwargs

    # Calculate expected time range
    now = datetime.now(timezone.utc)
    expected_start = int((now - timedelta(hours=48)).timestamp())
    expected_end = int(now.timestamp())

    # Allow 1 second tolerance for execution time
    assert abs(call_kwargs["start_time"] - expected_start) <= 1
    assert abs(call_kwargs["end_time"] - expected_end) <= 1


@pytest.mark.asyncio
@patch("reflector.worker.process.settings")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.recordings_controller.get_by_ids")
@patch("reflector.worker.process.process_multitrack_recording.delay")
async def test_poll_daily_recordings_default_lookback_window(
    mock_process_delay,
    mock_get_recordings,
    mock_create_client,
    mock_settings,
    mock_recording_response,
):
    """Test that poll_daily_recordings uses default 24-hour lookback when not configured."""
    # Use default lookback window
    mock_settings.DAILYCO_STORAGE_AWS_BUCKET_NAME = "test-bucket"
    mock_settings.DAILY_RECORDING_POLL_LOOKBACK_HOURS = 24

    # Mock Daily.co API client
    mock_daily_client = AsyncMock()
    mock_daily_client.list_recordings = AsyncMock(return_value=mock_recording_response)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # Mock DB controller - no existing recordings
    mock_get_recordings.return_value = []

    # Execute - call the unwrapped async function
    poll_fn = _get_poll_daily_recordings_fn()
    await poll_fn()

    # Verify Daily.co API was called with 24-hour window
    assert mock_daily_client.list_recordings.call_count == 1
    call_kwargs = mock_daily_client.list_recordings.call_args.kwargs

    now = datetime.now(timezone.utc)
    expected_start = int((now - timedelta(hours=24)).timestamp())
    expected_end = int(now.timestamp())

    # Allow 1 second tolerance
    assert abs(call_kwargs["start_time"] - expected_start) <= 1
    assert abs(call_kwargs["end_time"] - expected_end) <= 1


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
