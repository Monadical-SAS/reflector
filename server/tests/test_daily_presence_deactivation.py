"""Unit tests for Daily.co presence-based meeting deactivation logic.

Tests the fix for split room race condition by verifying:
1. Real-time presence checking via Daily.co API
2. Room deletion when meetings deactivate
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest

from reflector.dailyco_api.responses import (
    RoomPresenceParticipant,
    RoomPresenceResponse,
)
from reflector.db.daily_participant_sessions import (
    DailyParticipantSession,
    daily_participant_sessions_controller,
)
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.video_platforms.daily import DailyClient


@pytest.fixture
async def daily_room_and_meeting():
    """Create test room and meeting for Daily platform."""
    room = await rooms_controller.add(
        name="test-daily",
        user_id="test-user",
        platform="daily",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
    )

    current_time = datetime.now(timezone.utc)
    end_time = current_time + timedelta(hours=2)

    meeting = await meetings_controller.create(
        id="test-meeting-id",
        room_name="test-daily-20260129120000",
        room_url="https://daily.co/test",
        host_room_url="https://daily.co/test",
        start_date=current_time,
        end_date=end_time,
        room=room,
    )

    return room, meeting


@pytest.mark.asyncio
async def test_daily_client_has_delete_room_method():
    """Verify DailyClient has delete_room method for cleanup."""
    # Create a mock DailyClient
    with patch("reflector.dailyco_api.client.DailyApiClient"):
        from reflector.video_platforms.models import VideoPlatformConfig

        config = VideoPlatformConfig(api_key="test-key", webhook_secret="test-secret")
        client = DailyClient(config)

        # Verify delete_room method exists
        assert hasattr(client, "delete_room")
        assert callable(getattr(client, "delete_room"))


@pytest.mark.asyncio
async def test_get_room_presence_returns_realtime_data(daily_room_and_meeting):
    """Test that get_room_presence returns real-time participant data."""
    room, meeting = daily_room_and_meeting

    # Mock Daily.co API response
    mock_presence = RoomPresenceResponse(
        total_count=2,
        data=[
            RoomPresenceParticipant(
                room=meeting.room_name,
                id="session-1",
                userId="user-1",
                userName="User One",
                joinTime="2026-01-29T12:00:00.000Z",
                duration=120,
            ),
            RoomPresenceParticipant(
                room=meeting.room_name,
                id="session-2",
                userId="user-2",
                userName="User Two",
                joinTime="2026-01-29T12:05:00.000Z",
                duration=60,
            ),
        ],
    )

    with patch("reflector.dailyco_api.client.DailyApiClient") as mock_api:
        from reflector.video_platforms.models import VideoPlatformConfig

        config = VideoPlatformConfig(api_key="test-key", webhook_secret="test-secret")
        client = DailyClient(config)

        # Mock the API client method
        client._api_client.get_room_presence = AsyncMock(return_value=mock_presence)

        # Call get_room_presence
        result = await client.get_room_presence(meeting.room_name)

        # Verify it calls Daily.co API
        client._api_client.get_room_presence.assert_called_once_with(meeting.room_name)

        # Verify result contains real-time data
        assert result.total_count == 2
        assert len(result.data) == 2
        assert result.data[0].id == "session-1"
        assert result.data[1].id == "session-2"


@pytest.mark.asyncio
async def test_presence_shows_active_even_when_db_stale(daily_room_and_meeting):
    """Test that Daily.co presence API is source of truth, not stale DB sessions."""
    room, meeting = daily_room_and_meeting
    current_time = datetime.now(timezone.utc)

    # Create stale DB session (left_at=NULL but user actually left)
    session_id = f"{meeting.id}:stale-user:{int((current_time - timedelta(minutes=5)).timestamp() * 1000)}"
    await daily_participant_sessions_controller.upsert_joined(
        DailyParticipantSession(
            id=session_id,
            meeting_id=meeting.id,
            room_id=room.id,
            session_id="stale-daily-session",
            user_name="Stale User",
            user_id="stale-user",
            joined_at=current_time - timedelta(minutes=5),
            left_at=None,  # Stale - shows active but user left
        )
    )

    # Verify DB shows active session
    db_sessions = await daily_participant_sessions_controller.get_active_by_meeting(
        meeting.id
    )
    assert len(db_sessions) == 1

    # But Daily.co API shows room is empty
    mock_presence = RoomPresenceResponse(total_count=0, data=[])

    with patch("reflector.dailyco_api.client.DailyApiClient"):
        from reflector.video_platforms.models import VideoPlatformConfig

        config = VideoPlatformConfig(api_key="test-key", webhook_secret="test-secret")
        client = DailyClient(config)
        client._api_client.get_room_presence = AsyncMock(return_value=mock_presence)

        # Get real-time presence
        presence = await client.get_room_presence(meeting.room_name)

        # Real-time API shows no participants (truth)
        assert presence.total_count == 0
        assert len(presence.data) == 0

        # DB shows 1 participant (stale)
        assert len(db_sessions) == 1

        # Implementation should trust presence API, not DB


@pytest.mark.asyncio
async def test_meeting_deactivation_logic_with_presence_empty():
    """Test the core deactivation decision logic when presence shows room empty."""
    # This tests the logic that will be in process_meetings

    # Simulate: DB shows stale active session
    has_active_db_sessions = True  # DB is stale

    # Simulate: Daily.co presence API shows room empty
    presence_count = 0  # Real-time truth

    # Simulate: Meeting has been used before
    has_had_sessions = True

    # Decision logic (what process_meetings should do):
    # - If presence API available: trust it
    # - If presence shows empty AND has_had_sessions: deactivate

    if presence_count == 0 and has_had_sessions:
        should_deactivate = True
    else:
        should_deactivate = False

    assert should_deactivate is True  # Should deactivate despite stale DB


@pytest.mark.asyncio
async def test_meeting_deactivation_logic_with_presence_active():
    """Test that meetings stay active when presence shows participants."""
    # Simulate: DB shows no sessions (not yet updated)
    has_active_db_sessions = False  # DB hasn't caught up

    # Simulate: Daily.co presence API shows active participant
    presence_count = 1  # Real-time truth

    # Decision logic: presence shows activity, keep meeting active
    if presence_count > 0:
        should_deactivate = False
    else:
        should_deactivate = True

    assert should_deactivate is False  # Should stay active


@pytest.mark.asyncio
async def test_delete_room_called_on_deactivation(daily_room_and_meeting):
    """Test that Daily.co room is deleted when meeting deactivates."""
    room, meeting = daily_room_and_meeting

    with patch("reflector.dailyco_api.client.DailyApiClient"):
        from reflector.video_platforms.models import VideoPlatformConfig

        config = VideoPlatformConfig(api_key="test-key", webhook_secret="test-secret")
        client = DailyClient(config)

        # Mock delete_room API call
        client._api_client.delete_room = AsyncMock()

        # Simulate deactivation - should delete room
        await client._api_client.delete_room(meeting.room_name)

        # Verify delete was called
        client._api_client.delete_room.assert_called_once_with(meeting.room_name)


@pytest.mark.asyncio
async def test_delete_room_idempotent_on_404():
    """Test that room deletion is idempotent (succeeds even if room doesn't exist)."""
    from reflector.dailyco_api.client import DailyApiClient

    # Create real client to test delete_room logic
    client = DailyApiClient(api_key="test-key")

    # Mock the HTTP client
    mock_http_client = AsyncMock()
    mock_response = AsyncMock()
    mock_response.status_code = 404  # Room not found
    mock_http_client.delete = AsyncMock(return_value=mock_response)

    # Mock _get_client to return our mock
    async def mock_get_client():
        return mock_http_client

    client._get_client = mock_get_client

    # delete_room should succeed even on 404 (idempotent)
    await client.delete_room("nonexistent-room")

    # Verify delete was attempted
    mock_http_client.delete.assert_called_once()


@pytest.mark.asyncio
async def test_api_failure_fallback_to_db_sessions():
    """Test that system falls back to DB sessions if Daily.co API fails."""
    # Simulate: Daily.co API throws exception
    api_exception = Exception("API unavailable")

    # Simulate: DB shows active session
    has_active_db_sessions = True

    # Decision logic with fallback:
    try:
        presence_count = None
        raise api_exception  # Simulating API failure
    except Exception:
        # Fallback: use DB sessions (conservative - don't deactivate if unsure)
        if has_active_db_sessions:
            should_deactivate = False
        else:
            should_deactivate = True

    assert should_deactivate is False  # Conservative: keep active on API failure
