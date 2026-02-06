"""Tests for direct session close on participant.left webhook.

Verifies that _handle_participant_left:
1. Closes the session directly (authoritative signal)
2. Updates num_clients from remaining active sessions
3. Queues a delayed reconciliation poll as safety net
4. Handles missing session gracefully
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.dailyco_api.webhooks import ParticipantLeftEvent, ParticipantLeftPayload
from reflector.db.daily_participant_sessions import DailyParticipantSession
from reflector.db.meetings import Meeting
from reflector.views.daily import _handle_participant_left


@pytest.fixture
def mock_meeting():
    return Meeting(
        id="meeting-123",
        room_id="room-456",
        room_name="test-room-20251118120000",
        room_url="https://daily.co/test-room-20251118120000",
        host_room_url="https://daily.co/test-room-20251118120000?t=host-token",
        platform="daily",
        num_clients=2,
        is_active=True,
        start_date=datetime.now(timezone.utc),
        end_date=datetime.now(timezone.utc),
    )


@pytest.fixture
def participant_left_event():
    now = datetime.now(timezone.utc)
    return ParticipantLeftEvent(
        version="1.0.0",
        type="participant.left",
        id="evt-left-abc123",
        payload=ParticipantLeftPayload(
            room_name="test-room-20251118120000",
            session_id="session-alice",
            user_id="user-alice",
            user_name="Alice",
            joined_at=int((now - timedelta(minutes=10)).timestamp()),
            duration=600,
        ),
        event_ts=int(now.timestamp()),
    )


@pytest.fixture
def existing_session():
    now = datetime.now(timezone.utc)
    return DailyParticipantSession(
        id="meeting-123:session-alice",
        meeting_id="meeting-123",
        room_id="room-456",
        session_id="session-alice",
        user_id="user-alice",
        user_name="Alice",
        joined_at=now - timedelta(minutes=10),
        left_at=None,
    )


@pytest.mark.asyncio
@patch("reflector.views.daily.poll_daily_room_presence_task")
@patch("reflector.views.daily.meetings_controller")
@patch("reflector.views.daily.daily_participant_sessions_controller")
async def test_closes_session_and_updates_num_clients(
    mock_sessions_ctrl,
    mock_meetings_ctrl,
    mock_poll_task,
    mock_meeting,
    participant_left_event,
    existing_session,
):
    """Webhook directly closes session and updates num_clients from remaining active count."""
    mock_meetings_ctrl.get_by_room_name = AsyncMock(return_value=mock_meeting)
    mock_sessions_ctrl.get_open_session = AsyncMock(return_value=existing_session)
    mock_sessions_ctrl.batch_close_sessions = AsyncMock()
    # One remaining active session after close
    remaining = DailyParticipantSession(
        id="meeting-123:session-bob",
        meeting_id="meeting-123",
        room_id="room-456",
        session_id="session-bob",
        user_id="user-bob",
        user_name="Bob",
        joined_at=datetime.now(timezone.utc),
        left_at=None,
    )
    mock_sessions_ctrl.get_active_by_meeting = AsyncMock(return_value=[remaining])
    mock_meetings_ctrl.update_meeting = AsyncMock()

    await _handle_participant_left(participant_left_event)

    # Session closed
    mock_sessions_ctrl.batch_close_sessions.assert_called_once()
    closed_ids = mock_sessions_ctrl.batch_close_sessions.call_args.args[0]
    assert closed_ids == [existing_session.id]

    # num_clients updated to remaining count
    mock_meetings_ctrl.update_meeting.assert_called_once_with(
        mock_meeting.id, num_clients=1
    )

    # Delayed reconciliation poll queued
    mock_poll_task.apply_async.assert_called_once()
    call_kwargs = mock_poll_task.apply_async.call_args.kwargs
    assert call_kwargs["countdown"] == 5
    assert call_kwargs["args"] == [mock_meeting.id]


@pytest.mark.asyncio
@patch("reflector.views.daily.poll_daily_room_presence_task")
@patch("reflector.views.daily.meetings_controller")
@patch("reflector.views.daily.daily_participant_sessions_controller")
async def test_handles_missing_session(
    mock_sessions_ctrl,
    mock_meetings_ctrl,
    mock_poll_task,
    mock_meeting,
    participant_left_event,
):
    """No crash when session not found in DB — still queues reconciliation poll."""
    mock_meetings_ctrl.get_by_room_name = AsyncMock(return_value=mock_meeting)
    mock_sessions_ctrl.get_open_session = AsyncMock(return_value=None)

    await _handle_participant_left(participant_left_event)

    # No session close attempted
    mock_sessions_ctrl.batch_close_sessions.assert_not_called()
    # No num_clients update (no authoritative data without session)
    mock_meetings_ctrl.update_meeting.assert_not_called()
    # Still queues reconciliation poll
    mock_poll_task.apply_async.assert_called_once()


@pytest.mark.asyncio
@patch("reflector.views.daily.poll_daily_room_presence_task")
@patch("reflector.views.daily.meetings_controller")
@patch("reflector.views.daily.daily_participant_sessions_controller")
async def test_updates_num_clients_to_zero_when_last_participant_leaves(
    mock_sessions_ctrl,
    mock_meetings_ctrl,
    mock_poll_task,
    mock_meeting,
    participant_left_event,
    existing_session,
):
    """num_clients set to 0 when no active sessions remain."""
    mock_meetings_ctrl.get_by_room_name = AsyncMock(return_value=mock_meeting)
    mock_sessions_ctrl.get_open_session = AsyncMock(return_value=existing_session)
    mock_sessions_ctrl.batch_close_sessions = AsyncMock()
    mock_sessions_ctrl.get_active_by_meeting = AsyncMock(return_value=[])
    mock_meetings_ctrl.update_meeting = AsyncMock()

    await _handle_participant_left(participant_left_event)

    mock_meetings_ctrl.update_meeting.assert_called_once_with(
        mock_meeting.id, num_clients=0
    )


@pytest.mark.asyncio
@patch("reflector.views.daily.poll_daily_room_presence_task")
@patch("reflector.views.daily.meetings_controller")
async def test_no_room_name_in_event(
    mock_meetings_ctrl,
    mock_poll_task,
):
    """No crash when room_name is missing from webhook payload."""
    event = ParticipantLeftEvent(
        version="1.0.0",
        type="participant.left",
        id="evt-left-no-room",
        payload=ParticipantLeftPayload(
            room_name=None,
            session_id="session-x",
            user_id="user-x",
            user_name="X",
            joined_at=int(datetime.now(timezone.utc).timestamp()),
            duration=0,
        ),
        event_ts=int(datetime.now(timezone.utc).timestamp()),
    )

    await _handle_participant_left(event)

    mock_meetings_ctrl.get_by_room_name.assert_not_called()
    mock_poll_task.apply_async.assert_not_called()


@pytest.mark.asyncio
@patch("reflector.views.daily.poll_daily_room_presence_task")
@patch("reflector.views.daily.meetings_controller")
async def test_meeting_not_found(
    mock_meetings_ctrl,
    mock_poll_task,
    participant_left_event,
):
    """No crash when meeting not found for room_name."""
    mock_meetings_ctrl.get_by_room_name = AsyncMock(return_value=None)

    await _handle_participant_left(participant_left_event)

    mock_poll_task.apply_async.assert_not_called()
