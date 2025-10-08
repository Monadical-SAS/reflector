"""Tests for video platform clients."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.db.rooms import Room
from reflector.video_platforms.base import MeetingData, VideoPlatformConfig
from reflector.video_platforms.daily import DailyClient
from reflector.video_platforms.mock import MockPlatformClient
from reflector.video_platforms.registry import get_platform_client
from reflector.video_platforms.whereby import WherebyClient


@pytest.fixture
def mock_room():
    """Create a mock room for testing."""
    room = MagicMock(spec=Room)
    room.id = "test-room-123"
    room.name = "Test Room"
    room.recording_type = "cloud"
    room.platform = "whereby"
    return room


@pytest.fixture
def config():
    """Create a test configuration."""
    return VideoPlatformConfig(
        api_key="test-api-key",
        webhook_secret="test-webhook-secret",
        subdomain="test-subdomain",
    )


class TestPlatformFactory:
    """Test platform client factory."""

    def test_create_whereby_client(self, config):
        """Test creating Whereby client."""
        client = get_platform_client("whereby", config)
        assert isinstance(client, WherebyClient)

    def test_create_daily_client(self, config):
        """Test creating Daily client."""
        client = get_platform_client("daily", config)
        assert isinstance(client, DailyClient)

    def test_create_mock_client(self, config):
        """Test creating mock client."""
        client = get_platform_client("mock", config)
        assert isinstance(client, MockPlatformClient)

    def test_invalid_platform_raises_error(self, config):
        """Test that invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Unknown platform: invalid"):
            get_platform_client("invalid", config)


class TestMockPlatformClient:
    """Test mock platform client implementation."""

    @pytest.fixture
    def mock_client(self, config):
        return MockPlatformClient(config)

    @pytest.mark.asyncio
    async def test_create_meeting(self, mock_client, mock_room):
        """Test creating a meeting with mock client."""
        end_date = datetime.utcnow() + timedelta(hours=1)

        meeting_data = await mock_client.create_meeting(
            room_name_prefix="test", end_date=end_date, room=mock_room
        )

        assert isinstance(meeting_data, MeetingData)
        assert meeting_data.room_url.startswith("https://mock.video/")
        assert meeting_data.host_room_url.startswith("https://mock.video/")
        assert meeting_data.room_name.startswith("test")

    @pytest.mark.asyncio
    async def test_get_room_sessions(self, mock_client):
        """Test getting room sessions."""
        # First create a room so it exists
        end_date = datetime.utcnow() + timedelta(hours=1)
        mock_room = MagicMock()
        mock_room.id = "test-room"
        meeting = await mock_client.create_meeting("test", end_date, mock_room)

        sessions = await mock_client.get_room_sessions(meeting.room_name)
        assert isinstance(sessions, dict)
        assert "sessions" in sessions
        assert len(sessions["sessions"]) == 1

    @pytest.mark.asyncio
    async def test_delete_room(self, mock_client):
        """Test deleting a room."""
        # First create a room so it exists
        end_date = datetime.utcnow() + timedelta(hours=1)
        mock_room = MagicMock()
        mock_room.id = "test-room"
        meeting = await mock_client.create_meeting("test", end_date, mock_room)

        result = await mock_client.delete_room(meeting.room_name)
        assert result is True

    def test_verify_webhook_signature_valid(self, mock_client):
        """Test webhook signature verification with valid signature."""
        payload = b'{"event": "test"}'
        signature = "valid"  # Mock accepts "valid" as valid signature

        result = mock_client.verify_webhook_signature(payload, signature)
        assert result is True

    def test_verify_webhook_signature_invalid(self, mock_client):
        """Test webhook signature verification with invalid signature."""
        payload = b'{"event": "test"}'
        signature = "invalid-signature"

        result = mock_client.verify_webhook_signature(payload, signature)
        assert result is False


class TestDailyClient:
    """Test Daily platform client."""

    @pytest.fixture
    def daily_client(self, config):
        return DailyClient(config)

    @pytest.mark.asyncio
    async def test_create_meeting_success(self, daily_client, mock_room):
        """Test successful meeting creation."""
        end_date = datetime.utcnow() + timedelta(hours=1)

        mock_response = {
            "url": "https://test.daily.co/test-room-123-abc",
            "name": "test-room-123-abc",
            "api_created": True,
            "privacy": "public",
            "config": {"enable_recording": "cloud"},
        }

        with patch.object(
            daily_client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            meeting_data = await daily_client.create_meeting(
                room_name_prefix="test", end_date=end_date, room=mock_room
            )

            assert isinstance(meeting_data, MeetingData)
            assert meeting_data.room_url == "https://test.daily.co/test-room-123-abc"
            assert (
                meeting_data.host_room_url == "https://test.daily.co/test-room-123-abc"
            )
            assert meeting_data.room_name == "test-room-123-abc"

            # Verify request was made with correct parameters
            mock_request.assert_called_once()
            call_args = mock_request.call_args
            assert call_args[0][0] == "POST"
            assert "/rooms" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_room_sessions_success(self, daily_client):
        """Test successful room sessions retrieval."""
        mock_response = {
            "data": [
                {
                    "id": "session-1",
                    "room_name": "test-room",
                    "start_time": "2025-01-01T10:00:00Z",
                    "participants": [],
                }
            ]
        }

        with patch.object(
            daily_client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = mock_response

            sessions = await daily_client.get_room_sessions("test-room")

            assert isinstance(sessions, list)
            assert len(sessions) == 1
            assert sessions[0]["id"] == "session-1"

    @pytest.mark.asyncio
    async def test_delete_room_success(self, daily_client):
        """Test successful room deletion."""
        with patch.object(
            daily_client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {"deleted": True}

            result = await daily_client.delete_room("test-room")

            assert result is True
            mock_request.assert_called_once_with("DELETE", "/rooms/test-room")

    def test_verify_webhook_signature_valid(self, daily_client):
        """Test webhook signature verification with valid HMAC."""
        import hashlib
        import hmac

        payload = b'{"event": "participant.joined"}'
        expected_signature = hmac.new(
            daily_client.webhook_secret.encode(), payload, hashlib.sha256
        ).hexdigest()

        result = daily_client.verify_webhook_signature(payload, expected_signature)
        assert result is True

    def test_verify_webhook_signature_invalid(self, daily_client):
        """Test webhook signature verification with invalid HMAC."""
        payload = b'{"event": "participant.joined"}'
        invalid_signature = "invalid-signature"

        result = daily_client.verify_webhook_signature(payload, invalid_signature)
        assert result is False


class TestWherebyClient:
    """Test Whereby platform client."""

    @pytest.fixture
    def whereby_client(self, config):
        return WherebyClient(config)

    @pytest.mark.asyncio
    async def test_create_meeting_delegates_to_whereby_client(
        self, whereby_client, mock_room
    ):
        """Test that create_meeting delegates to existing Whereby client."""
        end_date = datetime.utcnow() + timedelta(hours=1)

        mock_whereby_response = {
            "roomUrl": "https://whereby.com/test-room",
            "hostRoomUrl": "https://whereby.com/test-room?host",
            "meetingId": "meeting-123",
        }

        with patch("reflector.video_platforms.whereby.whereby_client") as mock_client:
            mock_client.create_meeting.return_value = mock_whereby_response

            meeting_data = await whereby_client.create_meeting(
                room_name_prefix="test", end_date=end_date, room=mock_room
            )

            assert isinstance(meeting_data, MeetingData)
            assert meeting_data.room_url == "https://whereby.com/test-room"
            assert meeting_data.host_room_url == "https://whereby.com/test-room?host"
            assert meeting_data.meeting_id == "meeting-123"

    @pytest.mark.asyncio
    async def test_get_room_sessions_delegates_to_whereby_client(self, whereby_client):
        """Test that get_room_sessions delegates to existing Whereby client."""
        mock_sessions = [{"id": "session-1"}]

        with patch("reflector.video_platforms.whereby.whereby_client") as mock_client:
            mock_client.get_room_sessions.return_value = mock_sessions

            sessions = await whereby_client.get_room_sessions("test-room")

            assert sessions == mock_sessions

    def test_verify_webhook_signature_delegates_to_whereby_client(self, whereby_client):
        """Test that webhook verification delegates to existing Whereby client."""
        payload = b'{"event": "test"}'
        signature = "test-signature"

        with patch("reflector.video_platforms.whereby.whereby_client") as mock_client:
            mock_client.verify_webhook_signature.return_value = True

            result = whereby_client.verify_webhook_signature(payload, signature)

            assert result is True
            mock_client.verify_webhook_signature.assert_called_once_with(
                payload, signature
            )


class TestPlatformIntegration:
    """Integration tests for platform switching."""

    @pytest.mark.asyncio
    async def test_platform_switching_preserves_interface(self, config, mock_room):
        """Test that different platforms provide consistent interface."""
        end_date = datetime.utcnow() + timedelta(hours=1)

        # Test with mock platform
        mock_client = get_platform_client("mock", config)
        mock_meeting = await mock_client.create_meeting("test", end_date, mock_room)

        # Test with Daily platform (mocked)
        daily_client = get_platform_client("daily", config)
        with patch.object(
            daily_client, "_make_request", new_callable=AsyncMock
        ) as mock_request:
            mock_request.return_value = {
                "url": "https://test.daily.co/test-room",
                "name": "test-room",
                "api_created": True,
            }

            daily_meeting = await daily_client.create_meeting(
                "test", end_date, mock_room
            )

        # Both should return MeetingData objects with consistent fields
        assert isinstance(mock_meeting, MeetingData)
        assert isinstance(daily_meeting, MeetingData)

        # Both should have required fields
        for meeting in [mock_meeting, daily_meeting]:
            assert hasattr(meeting, "room_url")
            assert hasattr(meeting, "host_room_url")
            assert hasattr(meeting, "room_name")
            assert meeting.room_url.startswith("https://")
