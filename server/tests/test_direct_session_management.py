"""Tests for direct session management via /joined and /leave endpoints.

Verifies that:
1. /joined with session_id creates session directly, updates num_clients
2. /joined without session_id (backward compat) still works, queues poll
3. /leave with session_id closes session, updates num_clients
4. /leave without session_id falls back to poll
5. Duplicate /joined calls are idempotent (upsert)
6. /leave for already-closed session is a no-op
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.db.daily_participant_sessions import DailyParticipantSession
from reflector.db.meetings import Meeting
from reflector.views.rooms import (
    JoinedRequest,
    meeting_joined,
    meeting_leave,
)


@pytest.fixture
def mock_room():
    room = MagicMock()
    room.id = "room-456"
    room.name = "test-room"
    room.platform = "daily"
    return room


@pytest.fixture
def mock_meeting():
    return Meeting(
        id="meeting-123",
        room_id="room-456",
        room_name="test-room-20251118120000",
        room_url="https://daily.co/test-room",
        host_room_url="https://daily.co/test-room?t=host",
        platform="daily",
        num_clients=0,
        is_active=True,
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc) + timedelta(hours=8),
    )


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.aclose = AsyncMock()
    return redis


@pytest.fixture
def mock_request_with_session_id():
    """Mock Request with session_id in JSON body."""
    request = AsyncMock()
    request.body = AsyncMock(return_value=b'{"session_id": "session-abc"}')
    return request


@pytest.fixture
def mock_request_empty_body():
    """Mock Request with empty JSON body (old frontend / no frame access)."""
    request = AsyncMock()
    request.body = AsyncMock(return_value=b"{}")
    return request


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.delete_pending_join")
@patch("reflector.views.rooms.get_async_redis_client")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
@patch("reflector.views.rooms.daily_participant_sessions_controller")
async def test_joined_with_session_id_creates_session(
    mock_sessions_ctrl,
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_redis_client,
    mock_delete_pending,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_redis,
):
    """session_id in /joined -> create session + update num_clients."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)
    mock_redis_client.return_value = mock_redis
    mock_sessions_ctrl.batch_upsert_sessions = AsyncMock()
    mock_sessions_ctrl.get_active_by_meeting = AsyncMock(
        return_value=[MagicMock()]  # 1 active session
    )
    mock_meetings_ctrl.update_meeting = AsyncMock()

    body = JoinedRequest(
        connection_id="conn-1",
        session_id="session-abc",
        user_name="Alice",
    )
    result = await meeting_joined(
        "test-room", "meeting-123", body, user={"sub": "user-1"}
    )

    assert result.status == "ok"

    # Session created via upsert
    mock_sessions_ctrl.batch_upsert_sessions.assert_called_once()
    sessions = mock_sessions_ctrl.batch_upsert_sessions.call_args.args[0]
    assert len(sessions) == 1
    assert sessions[0].session_id == "session-abc"
    assert sessions[0].meeting_id == "meeting-123"
    assert sessions[0].room_id == "room-456"
    assert sessions[0].user_name == "Alice"
    assert sessions[0].user_id == "user-1"
    assert sessions[0].id == "meeting-123:session-abc"

    # num_clients updated
    mock_meetings_ctrl.update_meeting.assert_called_once_with(
        "meeting-123", num_clients=1
    )

    # Reconciliation poll still queued
    mock_poll_task.apply_async.assert_called_once()


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.delete_pending_join")
@patch("reflector.views.rooms.get_async_redis_client")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
@patch("reflector.views.rooms.daily_participant_sessions_controller")
async def test_joined_without_session_id_backward_compat(
    mock_sessions_ctrl,
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_redis_client,
    mock_delete_pending,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_redis,
):
    """No session_id in /joined -> no session create, still queues poll."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)
    mock_redis_client.return_value = mock_redis

    body = JoinedRequest(connection_id="conn-1")
    result = await meeting_joined(
        "test-room", "meeting-123", body, user={"sub": "user-1"}
    )

    assert result.status == "ok"
    mock_sessions_ctrl.batch_upsert_sessions.assert_not_called()
    mock_poll_task.apply_async.assert_called_once()


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.delete_pending_join")
@patch("reflector.views.rooms.get_async_redis_client")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
@patch("reflector.views.rooms.daily_participant_sessions_controller")
async def test_joined_anonymous_user_sets_null_user_id(
    mock_sessions_ctrl,
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_redis_client,
    mock_delete_pending,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_redis,
):
    """Anonymous user -> session.user_id is None, user_name defaults to 'Anonymous'."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)
    mock_redis_client.return_value = mock_redis
    mock_sessions_ctrl.batch_upsert_sessions = AsyncMock()
    mock_sessions_ctrl.get_active_by_meeting = AsyncMock(return_value=[MagicMock()])
    mock_meetings_ctrl.update_meeting = AsyncMock()

    body = JoinedRequest(connection_id="conn-1", session_id="session-abc")
    result = await meeting_joined("test-room", "meeting-123", body, user=None)

    assert result.status == "ok"
    sessions = mock_sessions_ctrl.batch_upsert_sessions.call_args.args[0]
    assert sessions[0].user_id is None
    assert sessions[0].user_name == "Anonymous"


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
@patch("reflector.views.rooms.daily_participant_sessions_controller")
async def test_leave_with_session_id_closes_session(
    mock_sessions_ctrl,
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_request_with_session_id,
):
    """session_id in /leave -> close session + update num_clients."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)

    existing_session = DailyParticipantSession(
        id="meeting-123:session-abc",
        meeting_id="meeting-123",
        room_id="room-456",
        session_id="session-abc",
        user_id="user-1",
        user_name="Alice",
        joined_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        left_at=None,
    )
    mock_sessions_ctrl.get_open_session = AsyncMock(return_value=existing_session)
    mock_sessions_ctrl.batch_close_sessions = AsyncMock()
    mock_sessions_ctrl.get_active_by_meeting = AsyncMock(return_value=[])
    mock_meetings_ctrl.update_meeting = AsyncMock()

    result = await meeting_leave(
        "test-room", "meeting-123", mock_request_with_session_id, user={"sub": "user-1"}
    )

    assert result.status == "ok"

    # Session closed
    mock_sessions_ctrl.batch_close_sessions.assert_called_once()
    closed_ids = mock_sessions_ctrl.batch_close_sessions.call_args.args[0]
    assert closed_ids == ["meeting-123:session-abc"]

    # num_clients updated
    mock_meetings_ctrl.update_meeting.assert_called_once_with(
        "meeting-123", num_clients=0
    )

    # No poll — direct close is authoritative, poll would race with API latency
    mock_poll_task.apply_async.assert_not_called()


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
async def test_leave_without_session_id_falls_back_to_poll(
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_request_empty_body,
):
    """No session_id in /leave -> just queues poll as before."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)

    result = await meeting_leave(
        "test-room", "meeting-123", mock_request_empty_body, user=None
    )

    assert result.status == "ok"
    mock_poll_task.apply_async.assert_called_once()


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.delete_pending_join")
@patch("reflector.views.rooms.get_async_redis_client")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
@patch("reflector.views.rooms.daily_participant_sessions_controller")
async def test_duplicate_joined_is_idempotent(
    mock_sessions_ctrl,
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_redis_client,
    mock_delete_pending,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_redis,
):
    """Calling /joined twice with same session_id -> upsert both times, no error."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)
    mock_redis_client.return_value = mock_redis
    mock_sessions_ctrl.batch_upsert_sessions = AsyncMock()
    mock_sessions_ctrl.get_active_by_meeting = AsyncMock(return_value=[MagicMock()])
    mock_meetings_ctrl.update_meeting = AsyncMock()

    body = JoinedRequest(
        connection_id="conn-1", session_id="session-abc", user_name="Alice"
    )
    await meeting_joined("test-room", "meeting-123", body, user={"sub": "user-1"})
    await meeting_joined("test-room", "meeting-123", body, user={"sub": "user-1"})

    assert mock_sessions_ctrl.batch_upsert_sessions.call_count == 2


@pytest.mark.asyncio
@patch("reflector.views.rooms.poll_daily_room_presence_task")
@patch("reflector.views.rooms.meetings_controller")
@patch("reflector.views.rooms.rooms_controller")
@patch("reflector.views.rooms.daily_participant_sessions_controller")
async def test_leave_already_closed_session_is_noop(
    mock_sessions_ctrl,
    mock_rooms_ctrl,
    mock_meetings_ctrl,
    mock_poll_task,
    mock_room,
    mock_meeting,
    mock_request_with_session_id,
):
    """/leave for already-closed session -> no close attempted, just poll."""
    mock_rooms_ctrl.get_by_name = AsyncMock(return_value=mock_room)
    mock_meetings_ctrl.get_by_id = AsyncMock(return_value=mock_meeting)
    mock_sessions_ctrl.get_open_session = AsyncMock(return_value=None)

    result = await meeting_leave(
        "test-room", "meeting-123", mock_request_with_session_id, user=None
    )

    assert result.status == "ok"
    mock_sessions_ctrl.batch_close_sessions.assert_not_called()
    mock_meetings_ctrl.update_meeting.assert_not_called()
    mock_poll_task.apply_async.assert_called_once()
