"""Integration tests for /joining and /joined endpoints.

Tests for the join intent tracking to prevent race conditions during
WebRTC handshake when users join meetings.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.db.meetings import Meeting
from reflector.presence.pending_joins import PENDING_JOIN_PREFIX

TEST_CONNECTION_ID = "test-connection-uuid-12345"


@pytest.fixture
def mock_room():
    """Mock room object."""
    from reflector.db.rooms import Room

    return Room(
        id="room-123",
        name="test-room",
        user_id="owner-user",
        created_at=datetime.now(timezone.utc),
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic",
        is_shared=True,
        platform="daily",
        skip_consent=False,
    )


@pytest.fixture
def mock_meeting():
    """Mock meeting object."""
    now = datetime.now(timezone.utc)
    return Meeting(
        id="meeting-456",
        room_id="room-123",
        room_name="test-room-20251118120000",
        room_url="https://daily.co/test-room-20251118120000",
        host_room_url="https://daily.co/test-room-20251118120000?t=host",
        platform="daily",
        num_clients=0,
        is_active=True,
        start_date=now,
        end_date=now + timedelta(hours=1),
    )


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
@patch("reflector.views.rooms.get_async_redis_client")
async def test_joining_endpoint_creates_pending_join(
    mock_get_redis,
    mock_get_meeting,
    mock_get_room,
    mock_room,
    mock_meeting,
    client,
    authenticated_client,
):
    """Test that /joining endpoint creates pending join in Redis."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = mock_meeting

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    response = await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify Redis setex was called with correct key pattern
    mock_redis.setex.assert_called_once()
    call_args = mock_redis.setex.call_args[0]
    assert call_args[0].startswith(f"{PENDING_JOIN_PREFIX}:{mock_meeting.id}:")
    assert TEST_CONNECTION_ID in call_args[0]


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
@patch("reflector.views.rooms.get_async_redis_client")
async def test_joined_endpoint_deletes_pending_join(
    mock_get_redis,
    mock_get_meeting,
    mock_get_room,
    mock_poll_task,
    mock_room,
    mock_meeting,
    client,
    authenticated_client,
):
    """Test that /joined endpoint deletes pending join from Redis."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = mock_meeting

    mock_redis = AsyncMock()
    mock_redis.delete = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    response = await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joined",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify Redis delete was called with correct key pattern
    mock_redis.delete.assert_called_once()
    call_args = mock_redis.delete.call_args[0]
    assert call_args[0].startswith(f"{PENDING_JOIN_PREFIX}:{mock_meeting.id}:")
    assert TEST_CONNECTION_ID in call_args[0]

    # Verify presence poll was triggered for Daily meetings
    mock_poll_task.delay.assert_called_once_with(mock_meeting.id)


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
async def test_joining_endpoint_room_not_found(
    mock_get_room,
    client,
    authenticated_client,
):
    """Test that /joining returns 404 when room not found."""
    mock_get_room.return_value = None

    response = await client.post(
        "/rooms/nonexistent-room/meetings/meeting-123/joining",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Room not found"


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
async def test_joining_endpoint_meeting_not_found(
    mock_get_meeting,
    mock_get_room,
    mock_room,
    client,
    authenticated_client,
):
    """Test that /joining returns 404 when meeting not found."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = None

    response = await client.post(
        f"/rooms/{mock_room.name}/meetings/nonexistent-meeting/joining",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Meeting not found"


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
async def test_joining_endpoint_meeting_not_active(
    mock_get_meeting,
    mock_get_room,
    mock_room,
    mock_meeting,
    client,
    authenticated_client,
):
    """Test that /joining returns 400 when meeting is not active."""
    mock_get_room.return_value = mock_room
    inactive_meeting = mock_meeting.model_copy(update={"is_active": False})
    mock_get_meeting.return_value = inactive_meeting

    response = await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Meeting is not active"


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
@patch("reflector.views.rooms.get_async_redis_client")
async def test_joining_endpoint_anonymous_user(
    mock_get_redis,
    mock_get_meeting,
    mock_get_room,
    mock_room,
    mock_meeting,
    client,
):
    """Test that /joining works for anonymous users with unique connection_id."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = mock_meeting

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    response = await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

    # Verify Redis setex was called with "anon:" prefix and connection_id
    call_args = mock_redis.setex.call_args[0]
    assert ":anon:" in call_args[0]
    assert TEST_CONNECTION_ID in call_args[0]


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
@patch("reflector.views.rooms.get_async_redis_client")
async def test_joining_endpoint_redis_closed_on_success(
    mock_get_redis,
    mock_get_meeting,
    mock_get_room,
    mock_room,
    mock_meeting,
    client,
    authenticated_client,
):
    """Test that Redis connection is closed after successful operation."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = mock_meeting

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
        json={"connection_id": TEST_CONNECTION_ID},
    )

    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
@patch("reflector.views.rooms.get_async_redis_client")
async def test_joining_endpoint_redis_closed_on_error(
    mock_get_redis,
    mock_get_meeting,
    mock_get_room,
    mock_room,
    mock_meeting,
    client,
    authenticated_client,
):
    """Test that Redis connection is closed even when operation fails."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = mock_meeting

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock(side_effect=Exception("Redis error"))
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    with pytest.raises(Exception):
        await client.post(
            f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
            json={"connection_id": TEST_CONNECTION_ID},
        )

    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_joining_endpoint_requires_connection_id(
    client,
):
    """Test that /joining returns 422 when connection_id is missing."""
    response = await client.post(
        "/rooms/test-room/meetings/meeting-123/joining",
        json={},
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_joining_endpoint_rejects_empty_connection_id(
    client,
):
    """Test that /joining returns 422 when connection_id is empty string."""
    response = await client.post(
        "/rooms/test-room/meetings/meeting-123/joining",
        json={"connection_id": ""},
    )

    assert response.status_code == 422  # Validation error (NonEmptyString)


@pytest.mark.asyncio
@patch("reflector.views.rooms.rooms_controller.get_by_name")
@patch("reflector.views.rooms.meetings_controller.get_by_id")
@patch("reflector.views.rooms.get_async_redis_client")
async def test_different_connection_ids_create_different_keys(
    mock_get_redis,
    mock_get_meeting,
    mock_get_room,
    mock_room,
    mock_meeting,
    client,
):
    """Test that different connection_ids create different Redis keys."""
    mock_get_room.return_value = mock_room
    mock_get_meeting.return_value = mock_meeting

    mock_redis = AsyncMock()
    mock_redis.setex = AsyncMock()
    mock_redis.aclose = AsyncMock()
    mock_get_redis.return_value = mock_redis

    # First connection
    await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
        json={"connection_id": "connection-1"},
    )
    key1 = mock_redis.setex.call_args[0][0]

    mock_redis.setex.reset_mock()

    # Second connection (different tab)
    await client.post(
        f"/rooms/{mock_room.name}/meetings/{mock_meeting.id}/joining",
        json={"connection_id": "connection-2"},
    )
    key2 = mock_redis.setex.call_args[0][0]

    # Keys should be different
    assert key1 != key2
    assert "connection-1" in key1
    assert "connection-2" in key2
