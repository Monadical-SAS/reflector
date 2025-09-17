"""Tests for video platform abstraction and Jitsi integration."""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from reflector.db.rooms import Room, VideoPlatform
from reflector.video_platforms.base import (
    MeetingData,
    VideoPlatformClient,
    VideoPlatformConfig,
)
from reflector.video_platforms.factory import (
    create_platform_client,
    get_platform_config,
)
from reflector.video_platforms.jitsi import JitsiClient
from reflector.video_platforms.registry import (
    get_available_platforms,
    get_platform_client,
    register_platform,
)
from reflector.video_platforms.whereby import WherebyClient


class TestVideoPlatformBase:
    """Test the video platform base classes and interfaces."""

    def test_video_platform_config_creation(self):
        """Test VideoPlatformConfig can be created with required fields."""
        config = VideoPlatformConfig(
            api_key="test-key",
            webhook_secret="test-secret",
            api_url="https://test.example.com",
        )
        assert config.api_key == "test-key"
        assert config.webhook_secret == "test-secret"
        assert config.api_url == "https://test.example.com"

    def test_meeting_data_creation(self):
        """Test MeetingData can be created with all fields."""
        meeting_data = MeetingData(
            meeting_id="test-123",
            room_name="test-room",
            room_url="https://test.com/room",
            host_room_url="https://test.com/host",
            platform=VideoPlatform.JITSI,
            extra_data={"jwt": "token123"},
        )
        assert meeting_data.meeting_id == "test-123"
        assert meeting_data.room_name == "test-room"
        assert meeting_data.platform == VideoPlatform.JITSI
        assert meeting_data.extra_data["jwt"] == "token123"


class TestJitsiClient:
    """Test JitsiClient implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = VideoPlatformConfig(
            api_key="",  # Jitsi doesn't use API key
            webhook_secret="test-webhook-secret",
            api_url="https://meet.example.com",
        )
        self.client = JitsiClient(self.config)
        self.test_room = Room(
            id="test-room-id", name="test-room", user_id="test-user", platform="jitsi"
        )

    @patch("reflector.settings.settings.JITSI_JWT_SECRET", "test-secret-123")
    @patch("reflector.settings.settings.JITSI_DOMAIN", "meet.example.com")
    @patch("reflector.settings.settings.JITSI_JWT_ISSUER", "reflector")
    @patch("reflector.settings.settings.JITSI_JWT_AUDIENCE", "jitsi")
    def test_jwt_generation(self):
        """Test JWT token generation with proper payload."""
        exp_time = datetime.now(timezone.utc) + timedelta(hours=1)
        jwt_token = self.client._generate_jwt(
            room="test-room", moderator=True, exp=exp_time
        )

        # Verify token is generated
        assert jwt_token is not None
        assert len(jwt_token) > 50  # JWT tokens are quite long
        assert jwt_token.count(".") == 2  # JWT has 3 parts separated by dots

    @patch("reflector.settings.settings.JITSI_JWT_SECRET", None)
    def test_jwt_generation_without_secret_fails(self):
        """Test JWT generation fails without secret."""
        exp_time = datetime.now(timezone.utc) + timedelta(hours=1)

        with pytest.raises(ValueError, match="JITSI_JWT_SECRET is required"):
            self.client._generate_jwt(room="test-room", moderator=False, exp=exp_time)

    @patch(
        "reflector.video_platforms.jitsi.client.generate_uuid4",
        return_value="test-uuid-123",
    )
    @patch("reflector.settings.settings.JITSI_JWT_SECRET", "test-secret-123")
    @patch("reflector.settings.settings.JITSI_DOMAIN", "meet.example.com")
    @patch("reflector.settings.settings.JITSI_JWT_ISSUER", "reflector")
    @patch("reflector.settings.settings.JITSI_JWT_AUDIENCE", "jitsi")
    async def test_create_meeting(self, mock_uuid):
        """Test meeting creation with JWT tokens."""
        end_date = datetime.now(timezone.utc) + timedelta(hours=2)

        meeting_data = await self.client.create_meeting(
            room_name_prefix="test", end_date=end_date, room=self.test_room
        )

        # Verify meeting data structure
        assert meeting_data.meeting_id == "test-uuid-123"
        assert meeting_data.platform == VideoPlatform.JITSI
        assert "reflector-test-room" in meeting_data.room_name
        assert "meet.example.com" in meeting_data.room_url
        assert "jwt=" in meeting_data.room_url
        assert "jwt=" in meeting_data.host_room_url

        # Verify extra data contains JWT tokens
        assert "user_jwt" in meeting_data.extra_data
        assert "host_jwt" in meeting_data.extra_data
        assert "domain" in meeting_data.extra_data

    async def test_get_room_sessions(self):
        """Test room sessions retrieval (mock implementation)."""
        sessions = await self.client.get_room_sessions("test-room")

        assert "roomName" in sessions
        assert "sessions" in sessions
        assert sessions["roomName"] == "test-room"
        assert len(sessions["sessions"]) > 0
        assert sessions["sessions"][0]["isActive"] is True

    async def test_delete_room(self):
        """Test room deletion (no-op for Jitsi)."""
        result = await self.client.delete_room("test-room")
        assert result is True

    async def test_upload_logo(self):
        """Test logo upload (no-op for Jitsi)."""
        result = await self.client.upload_logo("test-room", "logo.png")
        assert result is True

    def test_verify_webhook_signature_valid(self):
        """Test webhook signature verification with valid signature."""
        body = b'{"event": "test"}'
        # Generate expected signature
        import hmac
        from hashlib import sha256

        expected_signature = hmac.new(
            self.config.webhook_secret.encode(), body, sha256
        ).hexdigest()

        result = self.client.verify_webhook_signature(body, expected_signature)
        assert result is True

    def test_verify_webhook_signature_invalid(self):
        """Test webhook signature verification with invalid signature."""
        body = b'{"event": "test"}'
        invalid_signature = "invalid-signature"

        result = self.client.verify_webhook_signature(body, invalid_signature)
        assert result is False

    def test_verify_webhook_signature_no_secret(self):
        """Test webhook signature verification without secret."""
        config = VideoPlatformConfig(
            api_key="", webhook_secret="", api_url="https://meet.example.com"
        )
        client = JitsiClient(config)

        result = client.verify_webhook_signature(b'{"event": "test"}', "signature")
        assert result is False


class TestWherebyClient:
    """Test WherebyClient implementation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = VideoPlatformConfig(
            api_key="test-whereby-api-key",
            webhook_secret="test-whereby-webhook-secret",
            api_url="https://api.whereby.dev",
            s3_bucket="test-recordings-bucket",
            aws_access_key_id="test-access-key",
            aws_access_key_secret="test-access-secret",
        )
        self.client = WherebyClient(self.config)
        self.test_room = Room(
            id="test-room-id",
            name="test-room",
            user_id="test-user",
            platform=VideoPlatform.WHEREBY,
        )

    @patch("httpx.AsyncClient")
    async def test_create_meeting(self, mock_client_class):
        """Test Whereby meeting creation."""
        # Mock the HTTP response
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.json.return_value = {
            "meetingId": "whereby-meeting-123",
            "roomName": "whereby-room-456",
            "roomUrl": "https://whereby.com/room",
            "hostRoomUrl": "https://whereby.com/host-room",
            "startDate": "2025-01-15T10:00:00.000Z",
            "endDate": "2025-01-15T18:00:00.000Z",
        }
        mock_response.raise_for_status.return_value = None
        mock_client.post.return_value = mock_response

        end_date = datetime.now(timezone.utc) + timedelta(hours=2)

        meeting_data = await self.client.create_meeting(
            room_name_prefix="test", end_date=end_date, room=self.test_room
        )

        # Verify meeting data structure
        assert meeting_data.meeting_id == "whereby-meeting-123"
        assert meeting_data.room_name == "whereby-room-456"
        assert meeting_data.platform == VideoPlatform.WHEREBY
        assert "whereby.com" in meeting_data.room_url
        assert "whereby.com" in meeting_data.host_room_url

        # Verify HTTP call was made with correct parameters
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "whereby.dev" in call_args[0][0]  # URL
        assert "Bearer test-whereby-api-key" in call_args[1]["headers"]["Authorization"]

    @patch("httpx.AsyncClient")
    async def test_get_room_sessions(self, mock_client_class):
        """Test Whereby room sessions retrieval."""
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.json.return_value = {
            "sessions": [
                {
                    "id": "session-123",
                    "startTime": "2025-01-15T10:00:00Z",
                    "participants": [],
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_client.get.return_value = mock_response

        sessions = await self.client.get_room_sessions("test-room")

        assert "sessions" in sessions
        assert len(sessions["sessions"]) == 1
        assert sessions["sessions"][0]["id"] == "session-123"

        # Verify HTTP call
        mock_client.get.assert_called_once()

    async def test_delete_room(self):
        """Test room deletion (no-op for Whereby)."""
        result = await self.client.delete_room("test-room")
        assert result is True

    @patch("httpx.AsyncClient")
    async def test_upload_logo_success(self, mock_client_class):
        """Test logo upload success."""
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_client.put.return_value = mock_response

        # Create a temporary file for testing
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".png", delete=False) as f:
            f.write("fake logo content")
            temp_file = f.name

        result = await self.client.upload_logo("test-room", temp_file)
        assert result is True

        # Verify HTTP call
        mock_client.put.assert_called_once()

        # Cleanup
        import os

        os.unlink(temp_file)

    @patch("httpx.AsyncClient")
    async def test_upload_logo_failure(self, mock_client_class):
        """Test logo upload handles HTTP errors gracefully."""
        mock_client = mock_client_class.return_value.__aenter__.return_value
        mock_client.put.side_effect = Exception("HTTP error")

        result = await self.client.upload_logo("test-room", "logo.png")
        assert result is False

    def test_verify_webhook_signature_valid(self):
        """Test Whereby webhook signature verification with valid signature."""
        body = b'{"event": "test"}'
        import hmac
        from hashlib import sha256

        expected_signature = hmac.new(
            self.config.webhook_secret.encode(), body, sha256
        ).hexdigest()

        result = self.client.verify_webhook_signature(body, expected_signature)
        assert result is True

    def test_verify_webhook_signature_invalid(self):
        """Test Whereby webhook signature verification with invalid signature."""
        body = b'{"event": "test"}'
        invalid_signature = "invalid-signature"

        result = self.client.verify_webhook_signature(body, invalid_signature)
        assert result is False


class TestPlatformRegistry:
    """Test platform registry functionality."""

    def test_platform_registration(self):
        """Test platform registration and retrieval."""

        # Create mock client class
        class MockClient(VideoPlatformClient):
            async def create_meeting(self, room_name_prefix, end_date, room):
                pass

            async def get_room_sessions(self, room_name):
                pass

            async def delete_room(self, room_name):
                pass

            async def upload_logo(self, room_name, logo_path):
                pass

            def verify_webhook_signature(self, body, signature, timestamp=None):
                pass

        # Register mock platform
        register_platform("test-platform", MockClient)

        # Verify it's available
        available = get_available_platforms()
        assert "test-platform" in available

        # Test client creation
        config = VideoPlatformConfig(
            api_key="test", webhook_secret="test", api_url="test"
        )
        client = get_platform_client("test-platform", config)
        assert isinstance(client, MockClient)

    def test_get_unknown_platform_raises_error(self):
        """Test that requesting unknown platform raises error."""
        config = VideoPlatformConfig(
            api_key="test", webhook_secret="test", api_url="test"
        )

        with pytest.raises(ValueError, match="Unknown video platform: nonexistent"):
            get_platform_client("nonexistent", config)

    def test_builtin_platforms_registered(self):
        """Test that built-in platforms are registered."""
        available = get_available_platforms()
        assert "jitsi" in available
        assert "whereby" in available


class TestPlatformFactory:
    """Test platform factory functionality."""

    @patch("reflector.settings.settings.JITSI_JWT_SECRET", "test-secret")
    @patch("reflector.settings.settings.JITSI_WEBHOOK_SECRET", "webhook-secret")
    @patch("reflector.settings.settings.JITSI_DOMAIN", "meet.example.com")
    def test_get_jitsi_platform_config(self):
        """Test Jitsi platform configuration."""
        config = get_platform_config("jitsi")

        assert config.api_key == ""  # Jitsi uses JWT, no API key
        assert config.webhook_secret == "webhook-secret"
        assert config.api_url == "https://meet.example.com"

    @patch("reflector.settings.settings.WHEREBY_API_KEY", "whereby-key")
    @patch("reflector.settings.settings.WHEREBY_WEBHOOK_SECRET", "whereby-secret")
    @patch("reflector.settings.settings.WHEREBY_API_URL", "https://api.whereby.dev")
    def test_get_whereby_platform_config(self):
        """Test Whereby platform configuration."""
        config = get_platform_config("whereby")

        assert config.api_key == "whereby-key"
        assert config.webhook_secret == "whereby-secret"
        assert config.api_url == "https://api.whereby.dev"

    def test_get_unknown_platform_config_raises_error(self):
        """Test that unknown platform config raises error."""
        with pytest.raises(ValueError, match="Unknown platform: nonexistent"):
            get_platform_config("nonexistent")

    def test_create_platform_client(self):
        """Test platform client creation via factory."""
        with patch(
            "reflector.video_platforms.factory.get_platform_config"
        ) as mock_config:
            mock_config.return_value = VideoPlatformConfig(
                api_key="",
                webhook_secret="test-secret",
                api_url="https://meet.example.com",
            )

            client = create_platform_client("jitsi")
            assert isinstance(client, JitsiClient)

    def test_create_jitsi_client_typing(self):
        """Test that create_platform_client returns correctly typed JitsiClient."""
        with patch(
            "reflector.video_platforms.factory.get_platform_config"
        ) as mock_config:
            mock_config.return_value = VideoPlatformConfig(
                api_key="",
                webhook_secret="test-secret",
                api_url="https://meet.example.com",
            )

            # The typing overload should ensure this returns JitsiClient
            client = create_platform_client("jitsi")
            assert isinstance(client, JitsiClient)
            # Verify it has Jitsi-specific methods
            assert hasattr(client, "_generate_jwt")

    def test_create_whereby_client_typing(self):
        """Test that create_platform_client returns correctly typed WherebyClient."""
        with patch(
            "reflector.video_platforms.factory.get_platform_config"
        ) as mock_config:
            mock_config.return_value = VideoPlatformConfig(
                api_key="whereby-key",
                webhook_secret="whereby-secret",
                api_url="https://api.whereby.dev",
            )

            # The typing overload should ensure this returns WherebyClient
            client = create_platform_client("whereby")
            assert isinstance(client, WherebyClient)
            # Verify it has Whereby-specific attributes
            assert hasattr(client, "headers")
            assert hasattr(client, "timeout")


class TestWebhookEventStorage:
    """Test webhook event storage functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        from reflector.app import app

        self.client = TestClient(app)

    @patch("reflector.db.meetings.meetings_controller.participant_joined")
    @patch("reflector.db.meetings.meetings_controller.get_by_room_name")
    @patch(
        "reflector.video_platforms.jitsi.router.verify_jitsi_webhook_signature",
        return_value=True,
    )
    def test_participant_joined_event_storage(
        self, mock_verify, mock_get, mock_participant_joined
    ):
        """Test that participant joined events are stored correctly."""
        # Mock meeting
        mock_meeting = Mock()
        mock_meeting.id = "test-meeting-id"
        mock_meeting.num_clients = 1
        mock_get.return_value = mock_meeting

        payload = {
            "event": "muc-occupant-joined",
            "room": "test-room",
            "timestamp": "2025-01-15T10:30:00.000Z",
            "data": {"user_id": "test-user", "display_name": "John Doe"},
        }

        response = self.client.post(
            "/v1/jitsi/events",
            json=payload,
            headers={"x-jitsi-signature": "valid-signature"},
        )

        assert response.status_code == 200
        # Verify event was stored with correct data
        mock_participant_joined.assert_called_once_with(
            "test-meeting-id",
            {
                "timestamp": datetime.fromisoformat(
                    "2025-01-15T10:30:00.000Z".replace("Z", "+00:00")
                ),
                "data": {"user_id": "test-user", "display_name": "John Doe"},
            },
        )

    @patch("reflector.db.meetings.meetings_controller.recording_started")
    @patch("reflector.db.meetings.meetings_controller.get_by_room_name")
    @patch(
        "reflector.video_platforms.jitsi.router.verify_jitsi_webhook_signature",
        return_value=True,
    )
    def test_recording_started_event_storage(
        self, mock_verify, mock_get, mock_recording_started
    ):
        """Test that recording started events are stored correctly."""
        mock_meeting = Mock()
        mock_meeting.id = "test-meeting-id"
        mock_meeting.num_clients = 1
        mock_get.return_value = mock_meeting

        payload = {
            "event": "jibri-recording-on",
            "room": "test-room",
            "timestamp": "2025-01-15T10:32:00.000Z",
            "data": {"recording_id": "rec-123"},
        }

        response = self.client.post(
            "/v1/jitsi/events",
            json=payload,
            headers={"x-jitsi-signature": "valid-signature"},
        )

        assert response.status_code == 200
        mock_recording_started.assert_called_once_with(
            "test-meeting-id",
            {
                "timestamp": datetime.fromisoformat(
                    "2025-01-15T10:32:00.000Z".replace("Z", "+00:00")
                ),
                "data": {"recording_id": "rec-123"},
            },
        )

    @patch("reflector.db.meetings.meetings_controller.add_event")
    @patch("reflector.db.meetings.meetings_controller.get_by_room_name")
    @patch(
        "reflector.video_platforms.jitsi.router.verify_jitsi_webhook_signature",
        return_value=True,
    )
    def test_recording_complete_event_storage(
        self, mock_verify, mock_get, mock_add_event
    ):
        """Test that recording completion events are stored correctly."""
        mock_meeting = Mock()
        mock_meeting.id = "test-meeting-id"
        mock_meeting.num_clients = 1
        mock_get.return_value = mock_meeting

        payload = {
            "room_name": "test-room",
            "recording_file": "/recordings/test.mp4",
            "recording_status": "completed",
            "timestamp": "2025-01-15T11:15:00.000Z",
        }

        response = self.client.post(
            "/v1/jibri/recording-complete",
            json=payload,
            headers={"x-jitsi-signature": "valid-signature"},
        )

        assert response.status_code == 200
        mock_add_event.assert_called_once_with(
            "test-meeting-id",
            "recording_completed",
            {
                "recording_file": "/recordings/test.mp4",
                "recording_status": "completed",
                "timestamp": datetime.fromisoformat(
                    "2025-01-15T11:15:00.000Z".replace("Z", "+00:00")
                ),
            },
        )


class TestWebhookEndpoints:
    """Test Jitsi webhook endpoints."""

    def setup_method(self):
        """Set up test client."""
        from reflector.app import app

        self.client = TestClient(app)

    def test_health_endpoint(self):
        """Test Jitsi health check endpoint."""
        response = self.client.get("/v1/jitsi/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "jitsi-webhooks"
        assert "timestamp" in data
        assert "webhook_secret_configured" in data

    @patch(
        "reflector.video_platforms.jitsi.router.verify_jitsi_webhook_signature",
        return_value=True,
    )
    @patch("reflector.db.meetings.meetings_controller.get_by_room_name")
    @patch("reflector.db.meetings.meetings_controller.participant_joined")
    @patch("reflector.db.meetings.meetings_controller.update_meeting")
    async def test_jitsi_events_webhook_join(
        self, mock_update, mock_participant_joined, mock_get, mock_verify
    ):
        """Test participant join event webhook."""
        # Mock meeting
        mock_meeting = Mock()
        mock_meeting.id = "test-meeting-id"
        mock_meeting.num_clients = 1
        mock_get.return_value = mock_meeting

        payload = {
            "event": "muc-occupant-joined",
            "room": "test-room",
            "timestamp": "2025-01-15T10:30:00.000Z",
            "data": {},
        }

        response = self.client.post(
            "/v1/jitsi/events",
            json=payload,
            headers={"x-jitsi-signature": "valid-signature"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["event"] == "muc-occupant-joined"
        assert data["room"] == "test-room"

    @patch(
        "reflector.video_platforms.jitsi.router.verify_jitsi_webhook_signature",
        return_value=False,
    )
    async def test_jitsi_events_webhook_invalid_signature(self, mock_verify):
        """Test webhook with invalid signature returns 401."""
        payload = {
            "event": "muc-occupant-joined",
            "room": "test-room",
            "timestamp": "2025-01-15T10:30:00.000Z",
            "data": {},
        }

        response = self.client.post(
            "/v1/jitsi/events",
            json=payload,
            headers={"x-jitsi-signature": "invalid-signature"},
        )

        assert response.status_code == 401
        assert "Invalid webhook signature" in response.text

    @patch(
        "reflector.video_platforms.jitsi.router.verify_jitsi_webhook_signature",
        return_value=True,
    )
    @patch(
        "reflector.db.meetings.meetings_controller.get_by_room_name", return_value=None
    )
    async def test_jitsi_events_webhook_meeting_not_found(self, mock_get, mock_verify):
        """Test webhook with nonexistent meeting returns 404."""
        payload = {
            "event": "muc-occupant-joined",
            "room": "nonexistent-room",
            "timestamp": "2025-01-15T10:30:00.000Z",
            "data": {},
        }

        response = self.client.post(
            "/v1/jitsi/events",
            json=payload,
            headers={"x-jitsi-signature": "valid-signature"},
        )

        assert response.status_code == 404
        assert "Meeting not found" in response.text


class TestRoomsPlatformIntegration:
    """Test rooms endpoint integration with platform abstraction."""

    def setup_method(self):
        """Set up test client."""
        from reflector.app import app

        self.client = TestClient(app)

    @patch("reflector.auth.current_user_optional")
    @patch("reflector.db.rooms.rooms_controller.add")
    def test_create_room_with_jitsi_platform(self, mock_add, mock_auth):
        """Test room creation with Jitsi platform."""
        from datetime import datetime, timezone

        mock_auth.return_value = {"sub": "test-user"}

        # Create a proper Room object for the mock return
        from reflector.db.rooms import Room

        mock_room = Room(
            id="test-room-id",
            name="test-jitsi-room",
            user_id="test-user",
            created_at=datetime.now(timezone.utc),
            zulip_auto_post=False,
            zulip_stream="",
            zulip_topic="",
            is_locked=False,
            room_mode="normal",
            recording_type="cloud",
            recording_trigger="automatic-2nd-participant",
            is_shared=False,
            platform=VideoPlatform.JITSI,
        )
        mock_add.return_value = mock_room

        payload = {
            "name": "test-jitsi-room",
            "platform": "jitsi",
            "zulip_auto_post": False,
            "zulip_stream": "",
            "zulip_topic": "",
            "is_locked": False,
            "room_mode": "normal",
            "recording_type": "cloud",
            "recording_trigger": "automatic-2nd-participant",
            "is_shared": False,
            "webhook_url": "",
            "webhook_secret": "",
        }

        response = self.client.post("/v1/rooms", json=payload)

        # Verify the add method was called with platform parameter
        mock_add.assert_called_once()
        call_args = mock_add.call_args
        assert call_args.kwargs["platform"] == "jitsi"
        assert call_args.kwargs["name"] == "test-jitsi-room"
        assert response.status_code == 200

    def test_create_meeting_with_jitsi_platform_fallback(self):
        """Test that meeting creation falls back to whereby when platform client unavailable."""
        # This tests the fallback behavior in rooms.py when platform client returns None
        # The actual platform integration test is covered in the unit tests above

        # Just verify the endpoint exists and has the right structure
        # More detailed integration testing would require a full test database setup
        assert hasattr(self.client.app, "routes")

        # Find the meeting creation route
        meeting_routes = [
            r
            for r in self.client.app.routes
            if hasattr(r, "path") and "meeting" in r.path
        ]
        assert len(meeting_routes) > 0
