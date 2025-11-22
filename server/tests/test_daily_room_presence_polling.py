"""Tests for Daily.co room presence polling functionality.

TDD tests for Task 3.2: Room Presence Polling
- Query Daily.co API for current room participants
- Reconcile with DB sessions (add missing, close stale)
- Update meeting.num_clients if different
- Use batch operations for efficiency
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.dailyco_api.responses import (
    RoomPresenceParticipant,
    RoomPresenceResponse,
)
from reflector.db.daily_participant_sessions import DailyParticipantSession
from reflector.db.meetings import Meeting
from reflector.worker.process import poll_daily_room_presence


@pytest.fixture
def mock_meeting():
    """Mock meeting with Daily.co room."""
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
def mock_api_participants():
    """Mock Daily.co API presence response."""
    now = datetime.now(timezone.utc)
    return RoomPresenceResponse(
        total_count=2,
        data=[
            RoomPresenceParticipant(
                room="test-room-20251118120000",
                id="participant-1",
                userName="Alice",
                userId="user-alice",
                joinTime=(now - timedelta(minutes=10)).isoformat(),
                duration=600,
            ),
            RoomPresenceParticipant(
                room="test-room-20251118120000",
                id="participant-2",
                userName="Bob",
                userId="user-bob",
                joinTime=(now - timedelta(minutes=5)).isoformat(),
                duration=300,
            ),
        ],
    )


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.get_all_sessions_for_meeting"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_upsert_sessions"
)
async def test_poll_presence_adds_missing_sessions(
    mock_batch_upsert,
    mock_get_sessions,
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
    mock_api_participants,
):
    """Test that polling creates sessions for participants not in DB."""
    mock_get_by_id.return_value = mock_meeting

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(return_value=mock_api_participants)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    mock_get_sessions.return_value = {}
    mock_batch_upsert.return_value = None

    await poll_daily_room_presence(mock_meeting.id)

    assert mock_batch_upsert.call_count == 1
    sessions = mock_batch_upsert.call_args.args[0]
    assert len(sessions) == 2
    session_ids = {s.session_id for s in sessions}
    assert session_ids == {"participant-1", "participant-2"}


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.get_all_sessions_for_meeting"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_upsert_sessions"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_close_sessions"
)
async def test_poll_presence_closes_stale_sessions(
    mock_batch_close,
    mock_batch_upsert,
    mock_get_sessions,
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
    mock_api_participants,
):
    """Test that polling closes sessions for participants no longer in room."""
    mock_get_by_id.return_value = mock_meeting

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(return_value=mock_api_participants)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    now = datetime.now(timezone.utc)
    mock_get_sessions.return_value = {
        "participant-1": DailyParticipantSession(
            id=f"meeting-123:participant-1",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-1",
            user_id="user-alice",
            user_name="Alice",
            joined_at=now,
            left_at=None,
        ),
        "participant-stale": DailyParticipantSession(
            id=f"meeting-123:participant-stale",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-stale",
            user_id="user-stale",
            user_name="Stale User",
            joined_at=now - timedelta(seconds=120),  # Joined 2 minutes ago
            left_at=None,
        ),
    }

    await poll_daily_room_presence(mock_meeting.id)

    assert mock_batch_close.call_count == 1
    composite_ids = mock_batch_close.call_args.args[0]
    left_at = mock_batch_close.call_args.kwargs["left_at"]
    assert len(composite_ids) == 1
    assert "meeting-123:participant-stale" in composite_ids
    assert left_at is not None


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.get_all_sessions_for_meeting"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_upsert_sessions"
)
@patch("reflector.worker.process.meetings_controller.update_meeting")
async def test_poll_presence_updates_num_clients(
    mock_update_meeting,
    mock_batch_upsert,
    mock_get_sessions,
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
    mock_api_participants,
):
    """Test that polling updates num_clients when different from API."""
    meeting_with_wrong_count = mock_meeting
    meeting_with_wrong_count.num_clients = 5
    mock_get_by_id.return_value = meeting_with_wrong_count

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(return_value=mock_api_participants)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    mock_get_sessions.return_value = {}
    mock_batch_upsert.return_value = None

    await poll_daily_room_presence(meeting_with_wrong_count.id)

    assert mock_update_meeting.call_count == 1
    assert mock_update_meeting.call_args.kwargs["num_clients"] == 2


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.get_all_sessions_for_meeting"
)
async def test_poll_presence_no_changes_if_synced(
    mock_get_sessions,
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
    mock_api_participants,
):
    """Test that polling skips updates when DB already synced with API."""
    mock_get_by_id.return_value = mock_meeting

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(return_value=mock_api_participants)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    now = datetime.now(timezone.utc)
    mock_get_sessions.return_value = {
        "participant-1": DailyParticipantSession(
            id=f"meeting-123:participant-1",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-1",
            user_id="user-alice",
            user_name="Alice",
            joined_at=now,
            left_at=None,
        ),
        "participant-2": DailyParticipantSession(
            id=f"meeting-123:participant-2",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-2",
            user_id="user-bob",
            user_name="Bob",
            joined_at=now,
            left_at=None,
        ),
    }

    await poll_daily_room_presence(mock_meeting.id)


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.get_all_sessions_for_meeting"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_upsert_sessions"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_close_sessions"
)
async def test_poll_presence_mixed_add_and_remove(
    mock_batch_close,
    mock_batch_upsert,
    mock_get_sessions,
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
):
    """Test that polling handles simultaneous joins and leaves in single poll."""
    mock_get_by_id.return_value = mock_meeting

    now = datetime.now(timezone.utc)

    # API returns: participant-1 and participant-3 (new)
    api_response = RoomPresenceResponse(
        total_count=2,
        data=[
            RoomPresenceParticipant(
                room="test-room-20251118120000",
                id="participant-1",
                userName="Alice",
                userId="user-alice",
                joinTime=(now - timedelta(minutes=10)).isoformat(),
                duration=600,
            ),
            RoomPresenceParticipant(
                room="test-room-20251118120000",
                id="participant-3",
                userName="Charlie",
                userId="user-charlie",
                joinTime=now.isoformat(),
                duration=0,
            ),
        ],
    )

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(return_value=api_response)
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    # DB has: participant-1 and participant-2 (left but not in API)
    mock_get_sessions.return_value = {
        "participant-1": DailyParticipantSession(
            id=f"meeting-123:participant-1",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-1",
            user_id="user-alice",
            user_name="Alice",
            joined_at=now - timedelta(minutes=10),
            left_at=None,
        ),
        "participant-2": DailyParticipantSession(
            id=f"meeting-123:participant-2",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-2",
            user_id="user-bob",
            user_name="Bob",
            joined_at=now - timedelta(minutes=5),
            left_at=None,
        ),
    }

    mock_batch_upsert.return_value = None
    mock_batch_close.return_value = None

    await poll_daily_room_presence(mock_meeting.id)

    # Verify participant-3 was added (missing in DB)
    assert mock_batch_upsert.call_count == 1
    sessions_added = mock_batch_upsert.call_args.args[0]
    assert len(sessions_added) == 1
    assert sessions_added[0].session_id == "participant-3"
    assert sessions_added[0].user_name == "Charlie"

    # Verify participant-2 was closed (stale in DB)
    assert mock_batch_close.call_count == 1
    composite_ids = mock_batch_close.call_args.args[0]
    assert len(composite_ids) == 1
    assert "meeting-123:participant-2" in composite_ids


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
async def test_poll_presence_handles_api_error(
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
):
    """Test that polling handles Daily.co API errors gracefully."""
    mock_get_by_id.return_value = mock_meeting

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(side_effect=Exception("API error"))
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    await poll_daily_room_presence(mock_meeting.id)


@pytest.mark.asyncio
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.get_all_sessions_for_meeting"
)
@patch(
    "reflector.worker.process.daily_participant_sessions_controller.batch_close_sessions"
)
async def test_poll_presence_closes_all_when_room_empty(
    mock_batch_close,
    mock_get_sessions,
    mock_create_client,
    mock_get_by_id,
    mock_meeting,
):
    """Test that polling closes all sessions when room is empty."""
    mock_get_by_id.return_value = mock_meeting

    mock_daily_client = AsyncMock()
    mock_daily_client.get_room_presence = AsyncMock(
        return_value=RoomPresenceResponse(total_count=0, data=[])
    )
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    now = datetime.now(timezone.utc)
    mock_get_sessions.return_value = {
        "participant-1": DailyParticipantSession(
            id=f"meeting-123:participant-1",
            meeting_id="meeting-123",
            room_id="room-456",
            session_id="participant-1",
            user_id="user-alice",
            user_name="Alice",
            joined_at=now
            - timedelta(seconds=120),  # Joined 2 minutes ago (beyond grace period)
            left_at=None,
        ),
    }

    await poll_daily_room_presence(mock_meeting.id)

    assert mock_batch_close.call_count == 1
    composite_ids = mock_batch_close.call_args.args[0]
    left_at = mock_batch_close.call_args.kwargs["left_at"]
    assert len(composite_ids) == 1
    assert "meeting-123:participant-1" in composite_ids
    assert left_at is not None


@pytest.mark.asyncio
@patch("reflector.worker.process.RedisAsyncLock")
@patch("reflector.worker.process.meetings_controller.get_by_id")
@patch("reflector.worker.process.create_platform_client")
async def test_poll_presence_skips_if_locked(
    mock_create_client,
    mock_get_by_id,
    mock_redis_lock_class,
    mock_meeting,
):
    """Test that concurrent polling is prevented by Redis lock."""
    mock_get_by_id.return_value = mock_meeting

    # Mock the RedisAsyncLock to simulate lock not acquired
    mock_lock_instance = AsyncMock()
    mock_lock_instance.acquired = False  # Lock not acquired
    mock_lock_instance.__aenter__ = AsyncMock(return_value=mock_lock_instance)
    mock_lock_instance.__aexit__ = AsyncMock()

    mock_redis_lock_class.return_value = mock_lock_instance

    mock_daily_client = AsyncMock()
    mock_create_client.return_value.__aenter__ = AsyncMock(
        return_value=mock_daily_client
    )
    mock_create_client.return_value.__aexit__ = AsyncMock()

    await poll_daily_room_presence(mock_meeting.id)

    # Verify RedisAsyncLock was instantiated
    assert mock_redis_lock_class.call_count == 1
    # Verify get_room_presence was NOT called (lock not acquired, so function returned early)
    assert mock_daily_client.get_room_presence.call_count == 0
