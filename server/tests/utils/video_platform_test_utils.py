"""Utilities for testing video platform functionality."""

from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Any, Dict, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from reflector.db.rooms import Room
from reflector.video_platforms.base import MeetingData, VideoPlatformConfig
from reflector.video_platforms.factory import create_platform_client


class MockVideoPlatformTestHelper:
    """Helper class for testing with mock video platforms."""

    def __init__(self, platform: str = "mock"):
        self.platform = platform
        self.config = VideoPlatformConfig(
            api_key="test-api-key",
            webhook_secret="test-webhook-secret",
            subdomain="test-subdomain",
        )
        self.client = create_platform_client(platform, self.config)

    def create_mock_room(self, room_id: str = "test-room-123", **kwargs) -> MagicMock:
        """Create a mock room for testing."""
        room = MagicMock(spec=Room)
        room.id = room_id
        room.name = kwargs.get("name", "Test Room")
        room.recording_type = kwargs.get("recording_type", "cloud")
        room.platform = kwargs.get("platform", self.platform)
        return room

    async def create_test_meeting(
        self, room: Optional[Room] = None, **kwargs
    ) -> MeetingData:
        """Create a test meeting with default values."""
        if room is None:
            room = self.create_mock_room()

        end_date = kwargs.get("end_date", datetime.utcnow() + timedelta(hours=1))
        room_name_prefix = kwargs.get("room_name_prefix", "test")

        return await self.client.create_meeting(room_name_prefix, end_date, room)

    def create_webhook_event(
        self, event_type: str, room_name: str = "test-room-123-abc", **kwargs
    ) -> Dict[str, Any]:
        """Create a webhook event payload for testing."""
        if self.platform == "daily":
            return self._create_daily_webhook_event(event_type, room_name, **kwargs)
        elif self.platform == "whereby":
            return self._create_whereby_webhook_event(event_type, room_name, **kwargs)
        else:
            return {"type": event_type, "room_name": room_name, **kwargs}

    def _create_daily_webhook_event(
        self, event_type: str, room_name: str, **kwargs
    ) -> Dict[str, Any]:
        """Create Daily.co-specific webhook event."""
        base_event = {
            "type": event_type,
            "event_ts": int(datetime.utcnow().timestamp()),
            "room": {"name": room_name},
        }

        if event_type == "participant.joined" or event_type == "participant.left":
            base_event["participant"] = kwargs.get(
                "participant",
                {
                    "id": "participant-123",
                    "user_name": "Test User",
                    "session_id": "session-456",
                },
            )

        if event_type.startswith("recording."):
            base_event["recording"] = kwargs.get(
                "recording",
                {
                    "id": "recording-789",
                    "status": "finished" if "ready" in event_type else "recording",
                    "start_time": "2025-01-01T10:00:00Z",
                },
            )

            if "ready" in event_type:
                base_event["recording"]["download_url"] = (
                    "https://s3.amazonaws.com/bucket/recording.mp4"
                )
                base_event["recording"]["duration"] = 1800

        return base_event

    def _create_whereby_webhook_event(
        self, event_type: str, room_name: str, **kwargs
    ) -> Dict[str, Any]:
        """Create Whereby-specific webhook event."""
        # Whereby uses different event structure
        return {
            "event": event_type,
            "roomName": room_name,
            "timestamp": datetime.utcnow().isoformat(),
            **kwargs,
        }

    def mock_platform_responses(self, platform: str, responses: Dict[str, Any]):
        """Context manager to mock platform API responses."""
        if platform == "daily":
            return self._mock_daily_responses(responses)
        elif platform == "whereby":
            return self._mock_whereby_responses(responses)
        else:
            return self._mock_generic_responses(responses)

    @asynccontextmanager
    async def _mock_daily_responses(self, responses: Dict[str, Any]):
        """Mock Daily.co API responses."""
        with patch(
            "reflector.video_platforms.daily.DailyPlatformClient._make_request"
        ) as mock_request:
            mock_request.side_effect = lambda method, url, **kwargs: responses.get(
                f"{method} {url}", {}
            )
            yield mock_request

    @asynccontextmanager
    async def _mock_whereby_responses(self, responses: Dict[str, Any]):
        """Mock Whereby API responses."""
        with patch("reflector.video_platforms.whereby.whereby_client") as mock_client:
            for method, response in responses.items():
                setattr(mock_client, method, AsyncMock(return_value=response))
            yield mock_client

    @asynccontextmanager
    async def _mock_generic_responses(self, responses: Dict[str, Any]):
        """Mock generic platform responses."""
        yield responses


class IntegrationTestScenario:
    """Helper for running integration test scenarios across platforms."""

    def __init__(self, platforms: list = None):
        self.platforms = platforms or ["mock", "daily", "whereby"]
        self.helpers = {
            platform: MockVideoPlatformTestHelper(platform)
            for platform in self.platforms
        }

    async def test_meeting_lifecycle(self, room_config: Dict[str, Any] = None):
        """Test complete meeting lifecycle across all platforms."""
        results = {}

        for platform in self.platforms:
            helper = self.helpers[platform]
            room = helper.create_mock_room(**(room_config or {}))

            # Test meeting creation
            meeting = await helper.create_test_meeting(room=room)
            assert isinstance(meeting, MeetingData)
            assert meeting.room_url.startswith("https://")

            # Test room sessions
            sessions = await helper.client.get_room_sessions(meeting.room_name)
            assert isinstance(sessions, list)

            # Test room deletion
            deleted = await helper.client.delete_room(meeting.room_name)
            assert deleted is True

            results[platform] = {
                "meeting": meeting,
                "sessions": sessions,
                "deleted": deleted,
            }

        return results

    def test_webhook_signatures(self, payload: bytes = None):
        """Test webhook signature verification across platforms."""
        if payload is None:
            payload = b'{"event": "test"}'

        results = {}

        for platform in self.platforms:
            helper = self.helpers[platform]

            # Test valid signature
            if platform == "mock":
                valid_signature = "valid-signature"
            else:
                import hashlib
                import hmac

                valid_signature = hmac.new(
                    helper.config.webhook_secret.encode(), payload, hashlib.sha256
                ).hexdigest()

            valid_result = helper.client.verify_webhook_signature(
                payload, valid_signature
            )
            invalid_result = helper.client.verify_webhook_signature(
                payload, "invalid-signature"
            )

            results[platform] = {"valid": valid_result, "invalid": invalid_result}

        return results


def create_test_meeting_data(platform: str = "mock", **overrides) -> MeetingData:
    """Create test meeting data with platform-specific URLs."""
    base_data = {"room_name": "test-room-123-abc", "meeting_id": "meeting-456"}

    if platform == "daily":
        base_data.update(
            {
                "room_url": "https://test.daily.co/test-room-123-abc",
                "host_room_url": "https://test.daily.co/test-room-123-abc",
            }
        )
    elif platform == "whereby":
        base_data.update(
            {
                "room_url": "https://whereby.com/test-room-123-abc",
                "host_room_url": "https://whereby.com/test-room-123-abc?host",
            }
        )
    else:  # mock
        base_data.update(
            {
                "room_url": "https://mock.daily.co/test-room-123-abc",
                "host_room_url": "https://mock.daily.co/test-room-123-abc",
            }
        )

    base_data.update(overrides)
    return MeetingData(**base_data)


def assert_meeting_data_valid(meeting_data: MeetingData, platform: str = None):
    """Assert that meeting data is valid for the given platform."""
    assert isinstance(meeting_data, MeetingData)
    assert meeting_data.room_url.startswith("https://")
    assert meeting_data.host_room_url.startswith("https://")
    assert isinstance(meeting_data.room_name, str)
    assert len(meeting_data.room_name) > 0

    if platform == "daily":
        assert "daily.co" in meeting_data.room_url
    elif platform == "whereby":
        assert "whereby.com" in meeting_data.room_url
    elif platform == "mock":
        assert "mock.daily.co" in meeting_data.room_url
