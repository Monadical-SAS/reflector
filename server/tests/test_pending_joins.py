"""Tests for pending joins Redis helper functions.

TDD tests for tracking join intent to prevent race conditions during
WebRTC handshake when users join meetings.
"""

from unittest.mock import AsyncMock

import pytest

from reflector.presence.pending_joins import (
    PENDING_JOIN_PREFIX,
    PENDING_JOIN_TTL,
    create_pending_join,
    delete_pending_join,
    has_pending_joins,
)


@pytest.fixture
def mock_redis():
    """Mock async Redis client."""
    redis = AsyncMock()
    redis.setex = AsyncMock()
    redis.delete = AsyncMock()
    redis.scan = AsyncMock(return_value=(0, []))
    return redis


@pytest.mark.asyncio
async def test_create_pending_join_sets_key_with_ttl(mock_redis):
    """Test that create_pending_join stores key with correct TTL."""
    meeting_id = "meeting-123"
    user_id = "user-456"

    await create_pending_join(mock_redis, meeting_id, user_id)

    expected_key = f"{PENDING_JOIN_PREFIX}:{meeting_id}:{user_id}"
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args
    assert call_args[0][0] == expected_key
    assert call_args[0][1] == PENDING_JOIN_TTL
    # Value should be a timestamp string
    assert call_args[0][2] is not None


@pytest.mark.asyncio
async def test_delete_pending_join_removes_key(mock_redis):
    """Test that delete_pending_join removes the key."""
    meeting_id = "meeting-123"
    user_id = "user-456"

    await delete_pending_join(mock_redis, meeting_id, user_id)

    expected_key = f"{PENDING_JOIN_PREFIX}:{meeting_id}:{user_id}"
    mock_redis.delete.assert_called_once_with(expected_key)


@pytest.mark.asyncio
async def test_has_pending_joins_returns_false_when_no_keys(mock_redis):
    """Test has_pending_joins returns False when no matching keys."""
    mock_redis.scan.return_value = (0, [])

    result = await has_pending_joins(mock_redis, "meeting-123")

    assert result is False
    mock_redis.scan.assert_called_once()
    call_kwargs = mock_redis.scan.call_args.kwargs
    assert call_kwargs["match"] == f"{PENDING_JOIN_PREFIX}:meeting-123:*"


@pytest.mark.asyncio
async def test_has_pending_joins_returns_true_when_keys_exist(mock_redis):
    """Test has_pending_joins returns True when matching keys found."""
    mock_redis.scan.return_value = (0, [b"pending_join:meeting-123:user-1"])

    result = await has_pending_joins(mock_redis, "meeting-123")

    assert result is True


@pytest.mark.asyncio
async def test_has_pending_joins_scans_with_correct_pattern(mock_redis):
    """Test has_pending_joins uses correct scan pattern."""
    meeting_id = "meeting-abc-def"
    mock_redis.scan.return_value = (0, [])

    await has_pending_joins(mock_redis, meeting_id)

    expected_pattern = f"{PENDING_JOIN_PREFIX}:{meeting_id}:*"
    mock_redis.scan.assert_called_once()
    call_kwargs = mock_redis.scan.call_args.kwargs
    assert call_kwargs["match"] == expected_pattern
    assert call_kwargs["count"] == 100


@pytest.mark.asyncio
async def test_multiple_users_pending_joins(mock_redis):
    """Test that multiple users can have pending joins for same meeting."""
    meeting_id = "meeting-123"
    # Simulate two pending joins
    mock_redis.scan.return_value = (
        0,
        [b"pending_join:meeting-123:user-1", b"pending_join:meeting-123:user-2"],
    )

    result = await has_pending_joins(mock_redis, meeting_id)

    assert result is True


@pytest.mark.asyncio
async def test_pending_join_ttl_value():
    """Test that PENDING_JOIN_TTL has expected value."""
    # 30 seconds should be enough for WebRTC handshake but not too long
    assert PENDING_JOIN_TTL == 30


@pytest.mark.asyncio
async def test_pending_join_prefix_value():
    """Test that PENDING_JOIN_PREFIX has expected value."""
    assert PENDING_JOIN_PREFIX == "pending_join"


@pytest.mark.asyncio
async def test_has_pending_joins_multi_iteration_scan_no_keys(mock_redis):
    """Test has_pending_joins iterates until cursor returns 0."""
    # Simulate multi-iteration scan: cursor 100 -> cursor 50 -> cursor 0
    mock_redis.scan.side_effect = [
        (100, []),  # First iteration, no keys, continue
        (50, []),  # Second iteration, no keys, continue
        (0, []),  # Third iteration, cursor 0, done
    ]

    result = await has_pending_joins(mock_redis, "meeting-123")

    assert result is False
    assert mock_redis.scan.call_count == 3


@pytest.mark.asyncio
async def test_has_pending_joins_multi_iteration_finds_key_later(mock_redis):
    """Test has_pending_joins finds key on second iteration."""
    # Simulate finding key on second scan iteration
    mock_redis.scan.side_effect = [
        (100, []),  # First iteration, no keys
        (0, [b"pending_join:meeting-123:user-1"]),  # Second iteration, found key
    ]

    result = await has_pending_joins(mock_redis, "meeting-123")

    assert result is True
    assert mock_redis.scan.call_count == 2
