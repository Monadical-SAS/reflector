"""Tests for process_meetings pending joins check.

Tests that process_meetings correctly skips deactivation when
pending joins exist for a meeting.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.meetings import Meeting


def _get_process_meetings_fn():
    """Get the underlying async function without Celery/asynctask decorators."""
    from reflector.worker import process

    fn = process.process_meetings
    # Get through both decorator layers (@shared_task and @asynctask)
    if hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    if hasattr(fn, "__wrapped__"):
        fn = fn.__wrapped__
    return fn


@pytest.fixture
def mock_active_meeting():
    """Mock an active meeting that should be considered for deactivation."""
    now = datetime.now(timezone.utc)
    return Meeting(
        id="meeting-123",
        room_id="room-456",
        room_name="test-room-20251118120000",
        room_url="https://daily.co/test-room-20251118120000",
        host_room_url="https://daily.co/test-room-20251118120000?t=host",
        platform="daily",
        num_clients=0,
        is_active=True,
        start_date=now - timedelta(hours=1),
        end_date=now - timedelta(minutes=30),  # Already ended
    )


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_all_active")
@patch("reflector.worker.process.RedisAsyncLock")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.get_async_redis_client")
@patch("reflector.worker.process.has_pending_joins")
@patch("reflector.worker.process.meetings_controller.update_meeting")
async def test_process_meetings_skips_deactivation_with_pending_joins(
    mock_update_meeting,
    mock_has_pending_joins,
    mock_get_redis,
    mock_create_client,
    mock_redis_lock_class,
    mock_get_all_active,
    mock_active_meeting,
):
    """Test that process_meetings skips deactivation when pending joins exist."""
    process_meetings = _get_process_meetings_fn()

    mock_get_all_active.return_value = [mock_active_meeting]

    # Mock lock acquired
    mock_lock_instance = AsyncMock()
    mock_lock_instance.acquired = True
    mock_lock_instance.__aenter__ = AsyncMock(return_value=mock_lock_instance)
    mock_lock_instance.__aexit__ = AsyncMock()
    mock_redis_lock_class.return_value = mock_lock_instance

    # Mock platform client - no active sessions, but had sessions (triggers deactivation)
    mock_daily_client = AsyncMock()
    mock_session = AsyncMock()
    mock_session.ended_at = datetime.now(timezone.utc)  # Session ended
    mock_daily_client.get_room_sessions = AsyncMock(return_value=[mock_session])
    mock_create_client.return_value = mock_daily_client

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    # Mock pending joins exist
    mock_has_pending_joins.return_value = True

    await process_meetings()

    # Verify has_pending_joins was called
    mock_has_pending_joins.assert_called_once_with(mock_redis, mock_active_meeting.id)

    # Verify meeting was NOT deactivated
    mock_update_meeting.assert_not_called()

    # Verify Redis was closed
    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_all_active")
@patch("reflector.worker.process.RedisAsyncLock")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.get_async_redis_client")
@patch("reflector.worker.process.has_pending_joins")
@patch("reflector.worker.process.meetings_controller.update_meeting")
async def test_process_meetings_deactivates_without_pending_joins(
    mock_update_meeting,
    mock_has_pending_joins,
    mock_get_redis,
    mock_create_client,
    mock_redis_lock_class,
    mock_get_all_active,
    mock_active_meeting,
):
    """Test that process_meetings deactivates when no pending joins."""
    process_meetings = _get_process_meetings_fn()

    mock_get_all_active.return_value = [mock_active_meeting]

    # Mock lock acquired
    mock_lock_instance = AsyncMock()
    mock_lock_instance.acquired = True
    mock_lock_instance.__aenter__ = AsyncMock(return_value=mock_lock_instance)
    mock_lock_instance.__aexit__ = AsyncMock()
    mock_redis_lock_class.return_value = mock_lock_instance

    # Mock platform client - no active sessions, but had sessions
    mock_daily_client = AsyncMock()
    mock_session = AsyncMock()
    mock_session.ended_at = datetime.now(timezone.utc)
    mock_daily_client.get_room_sessions = AsyncMock(return_value=[mock_session])
    mock_create_client.return_value = mock_daily_client

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    # Mock no pending joins
    mock_has_pending_joins.return_value = False

    await process_meetings()

    # Verify meeting was deactivated
    mock_update_meeting.assert_called_once_with(mock_active_meeting.id, is_active=False)


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_all_active")
@patch("reflector.worker.process.RedisAsyncLock")
@patch("reflector.worker.process.create_platform_client")
async def test_process_meetings_no_check_when_active_sessions(
    mock_create_client,
    mock_redis_lock_class,
    mock_get_all_active,
    mock_active_meeting,
):
    """Test that pending joins check is skipped when there are active sessions."""
    process_meetings = _get_process_meetings_fn()

    mock_get_all_active.return_value = [mock_active_meeting]

    # Mock lock acquired
    mock_lock_instance = AsyncMock()
    mock_lock_instance.acquired = True
    mock_lock_instance.__aenter__ = AsyncMock(return_value=mock_lock_instance)
    mock_lock_instance.__aexit__ = AsyncMock()
    mock_redis_lock_class.return_value = mock_lock_instance

    # Mock platform client - has active session
    mock_daily_client = AsyncMock()
    mock_session = AsyncMock()
    mock_session.ended_at = None  # Still active
    mock_daily_client.get_room_sessions = AsyncMock(return_value=[mock_session])
    mock_create_client.return_value = mock_daily_client

    with (
        patch("reflector.worker.process.get_async_redis_client") as mock_get_redis,
        patch("reflector.worker.process.has_pending_joins") as mock_has_pending_joins,
        patch(
            "reflector.worker.process.meetings_controller.update_meeting"
        ) as mock_update_meeting,
    ):
        await process_meetings()

        # Verify pending joins check was NOT called (no need - active sessions exist)
        mock_has_pending_joins.assert_not_called()

        # Verify meeting was NOT deactivated
        mock_update_meeting.assert_not_called()


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_all_active")
@patch("reflector.worker.process.RedisAsyncLock")
@patch("reflector.worker.process.create_platform_client")
@patch("reflector.worker.process.get_async_redis_client")
@patch("reflector.worker.process.has_pending_joins")
@patch("reflector.worker.process.meetings_controller.update_meeting")
async def test_process_meetings_closes_redis_even_on_continue(
    mock_update_meeting,
    mock_has_pending_joins,
    mock_get_redis,
    mock_create_client,
    mock_redis_lock_class,
    mock_get_all_active,
    mock_active_meeting,
):
    """Test that Redis connection is always closed, even when skipping deactivation."""
    process_meetings = _get_process_meetings_fn()

    mock_get_all_active.return_value = [mock_active_meeting]

    # Mock lock acquired
    mock_lock_instance = AsyncMock()
    mock_lock_instance.acquired = True
    mock_lock_instance.__aenter__ = AsyncMock(return_value=mock_lock_instance)
    mock_lock_instance.__aexit__ = AsyncMock()
    mock_redis_lock_class.return_value = mock_lock_instance

    # Mock platform client - no active sessions
    mock_daily_client = AsyncMock()
    mock_session = AsyncMock()
    mock_session.ended_at = datetime.now(timezone.utc)
    mock_daily_client.get_room_sessions = AsyncMock(return_value=[mock_session])
    mock_create_client.return_value = mock_daily_client

    # Mock Redis client
    mock_redis = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    # Mock pending joins exist (will trigger continue)
    mock_has_pending_joins.return_value = True

    await process_meetings()

    # Verify Redis was closed
    mock_redis.aclose.assert_called_once()
