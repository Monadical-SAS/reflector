"""Tests for Daily.co webhook integration."""

import hashlib
import hmac
import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

from reflector.app import app
from reflector.views.dailyco import DailyCoWebhookEvent


class TestDailyCoWebhookIntegration:
    """Test Daily.co webhook endpoint integration."""

    @pytest.fixture
    def webhook_secret(self):
        """Test webhook secret."""
        return "test-webhook-secret-123"

    @pytest.fixture
    def mock_room(self):
        """Create a mock room for testing."""
        room = MagicMock()
        room.id = "test-room-123"
        room.name = "Test Room"
        room.recording_type = "cloud"
        room.platform = "dailyco"
        return room

    @pytest.fixture
    def mock_meeting(self):
        """Create a mock meeting for testing."""
        meeting = MagicMock()
        meeting.id = "test-meeting-456"
        meeting.room_id = "test-room-123"
        meeting.platform = "dailyco"
        meeting.room_name = "test-room-123-abc"
        return meeting

    def create_webhook_signature(self, payload: bytes, secret: str) -> str:
        """Create HMAC signature for webhook payload."""
        return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

    def create_webhook_event(
        self, event_type: str, room_name: str = "test-room-123-abc", **kwargs
    ) -> dict:
        """Create a Daily.co webhook event payload."""
        base_event = {
            "type": event_type,
            "id": f"evt_{event_type.replace('.', '_')}_{int(datetime.utcnow().timestamp())}",
            "ts": int(datetime.utcnow().timestamp() * 1000),  # milliseconds
            "data": {"room": {"name": room_name}, **kwargs},
        }
        return base_event

    @pytest.mark.asyncio
    async def test_webhook_participant_joined(
        self, webhook_secret, mock_room, mock_meeting
    ):
        """Test participant joined webhook event."""
        event_data = self.create_webhook_event(
            "participant.joined",
            participant={
                "id": "participant-123",
                "user_name": "John Doe",
                "session_id": "session-456",
            },
        )

        payload = json.dumps(event_data).encode()
        signature = self.create_webhook_signature(payload, webhook_secret)

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            with patch(
                "reflector.db.meetings.meetings_controller.get_by_room_name"
            ) as mock_get_meeting:
                mock_get_meeting.return_value = mock_meeting

                with patch(
                    "reflector.db.meetings.meetings_controller.update_meeting"
                ) as _mock_update:
                    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                        response = await ac.post(
                            "/dailyco_webhook",
                            json=event_data,
                            headers={"X-Daily-Signature": signature},
                        )

                        assert response.status_code == 200
                        assert response.json() == {"status": "ok"}

                        # Verify meeting was looked up
                        mock_get_meeting.assert_called_once_with("test-room-123-abc")

    @pytest.mark.asyncio
    async def test_webhook_participant_left(
        self, webhook_secret, mock_room, mock_meeting
    ):
        """Test participant left webhook event."""
        event_data = self.create_webhook_event(
            "participant.left",
            participant={
                "id": "participant-123",
                "user_name": "John Doe",
                "session_id": "session-456",
            },
        )

        payload = json.dumps(event_data).encode()
        signature = self.create_webhook_signature(payload, webhook_secret)

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            with patch(
                "reflector.db.meetings.meetings_controller.get_by_room_name"
            ) as mock_get_meeting:
                mock_get_meeting.return_value = mock_meeting

                async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                    response = await ac.post(
                        "/daily_webhook",
                        json=event_data,
                        headers={"X-Daily-Signature": signature},
                    )

                    assert response.status_code == 200
                    assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_webhook_recording_started(
        self, webhook_secret, mock_room, mock_meeting
    ):
        """Test recording started webhook event."""
        event_data = self.create_webhook_event(
            "recording.started",
            recording={
                "id": "recording-789",
                "status": "recording",
                "start_time": "2025-01-01T10:00:00Z",
            },
        )

        payload = json.dumps(event_data).encode()
        signature = self.create_webhook_signature(payload, webhook_secret)

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            with patch(
                "reflector.db.meetings.meetings_controller.get_by_room_name"
            ) as mock_get_meeting:
                mock_get_meeting.return_value = mock_meeting

                with patch(
                    "reflector.db.meetings.meetings_controller.update_meeting"
                ) as _mock_update:
                    async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                        response = await ac.post(
                            "/dailyco_webhook",
                            json=event_data,
                            headers={"X-Daily-Signature": signature},
                        )

                        assert response.status_code == 200
                        assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_webhook_recording_ready_triggers_processing(
        self, webhook_secret, mock_room, mock_meeting
    ):
        """Test recording ready webhook triggers audio processing."""
        event_data = self.create_webhook_event(
            "recording.ready-to-download",
            recording={
                "id": "recording-789",
                "status": "finished",
                "download_url": "https://s3.amazonaws.com/bucket/recording.mp4",
                "start_time": "2025-01-01T10:00:00Z",
                "duration": 1800,
            },
        )

        payload = json.dumps(event_data).encode()
        signature = self.create_webhook_signature(payload, webhook_secret)

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            with patch(
                "reflector.db.meetings.meetings_controller.get_by_room_name"
            ) as mock_get_meeting:
                mock_get_meeting.return_value = mock_meeting

                with patch(
                    "reflector.db.meetings.meetings_controller.update_meeting"
                ) as _mock_update_url:
                    with patch(
                        "reflector.worker.process.process_recording_from_url.delay"
                    ) as mock_process:
                        async with AsyncClient(
                            app=app, base_url="http://test/v1"
                        ) as ac:
                            response = await ac.post(
                                "/dailyco_webhook",
                                json=event_data,
                                headers={"X-Daily-Signature": signature},
                            )

                            assert response.status_code == 200
                            assert response.json() == {"status": "ok"}

                            # Verify processing was triggered with correct parameters
                            mock_process.assert_called_once_with(
                                recording_url="https://s3.amazonaws.com/bucket/recording.mp4",
                                meeting_id=mock_meeting.id,
                                recording_id="recording-789",
                            )

    @pytest.mark.asyncio
    async def test_webhook_invalid_signature_rejected(self, webhook_secret):
        """Test webhook with invalid signature is rejected."""
        event_data = self.create_webhook_event("participant.joined")

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                response = await ac.post(
                    "/daily_webhook",
                    json=event_data,
                    headers={"X-Daily-Signature": "invalid-signature"},
                )

                assert response.status_code == 401
                assert "Invalid signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_missing_signature_rejected(self):
        """Test webhook without signature header is rejected."""
        event_data = self.create_webhook_event("participant.joined")

        async with AsyncClient(app=app, base_url="http://test/v1") as ac:
            response = await ac.post("/daily_webhook", json=event_data)

            assert response.status_code == 401
            assert "Missing signature" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_meeting_not_found(self, webhook_secret):
        """Test webhook for non-existent meeting."""
        event_data = self.create_webhook_event(
            "participant.joined", room_name="non-existent-room"
        )

        payload = json.dumps(event_data).encode()
        signature = self.create_webhook_signature(payload, webhook_secret)

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            with patch(
                "reflector.db.meetings.meetings_controller.get_by_room_name"
            ) as mock_get_meeting:
                mock_get_meeting.return_value = None

                async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                    response = await ac.post(
                        "/daily_webhook",
                        json=event_data,
                        headers={"X-Daily-Signature": signature},
                    )

                    assert response.status_code == 404
                    assert "Meeting not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_webhook_unknown_event_type(self, webhook_secret, mock_meeting):
        """Test webhook with unknown event type."""
        event_data = self.create_webhook_event("unknown.event")

        payload = json.dumps(event_data).encode()
        signature = self.create_webhook_signature(payload, webhook_secret)

        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            with patch(
                "reflector.db.meetings.meetings_controller.get_by_room_name"
            ) as mock_get_meeting:
                mock_get_meeting.return_value = mock_meeting

                async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                    response = await ac.post(
                        "/daily_webhook",
                        json=event_data,
                        headers={"X-Daily-Signature": signature},
                    )

                    # Should still return 200 but log the unknown event
                    assert response.status_code == 200
                    assert response.json() == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_webhook_malformed_json(self, webhook_secret):
        """Test webhook with malformed JSON."""
        with patch("reflector.views.dailyco.settings") as mock_settings:
            mock_settings.DAILYCO_WEBHOOK_SECRET = webhook_secret

            async with AsyncClient(app=app, base_url="http://test/v1") as ac:
                response = await ac.post(
                    "/daily_webhook",
                    content="invalid json",
                    headers={
                        "Content-Type": "application/json",
                        "X-Daily-Signature": "test-signature",
                    },
                )

                assert response.status_code == 422  # Validation error


class TestWebhookEventValidation:
    """Test webhook event data validation."""

    def test_daily_webhook_event_validation_valid(self):
        """Test valid webhook event passes validation."""
        event_data = {
            "type": "participant.joined",
            "id": "evt_123",
            "ts": 1640995200000,  # milliseconds
            "data": {
                "room": {"name": "test-room"},
                "participant": {
                    "id": "participant-123",
                    "user_name": "John Doe",
                    "session_id": "session-456",
                },
            },
        }

        event = DailyCoWebhookEvent(**event_data)
        assert event.type == "participant.joined"
        assert event.data["room"]["name"] == "test-room"
        assert event.data["participant"]["id"] == "participant-123"

    def test_daily_webhook_event_validation_minimal(self):
        """Test minimal valid webhook event."""
        event_data = {
            "type": "room.created",
            "id": "evt_123",
            "ts": 1640995200000,
            "data": {"room": {"name": "test-room"}},
        }

        event = DailyCoWebhookEvent(**event_data)
        assert event.type == "room.created"
        assert event.data["room"]["name"] == "test-room"

    def test_daily_webhook_event_validation_with_recording(self):
        """Test webhook event with recording data."""
        event_data = {
            "type": "recording.ready-to-download",
            "id": "evt_123",
            "ts": 1640995200000,
            "data": {
                "room": {"name": "test-room"},
                "recording": {
                    "id": "recording-123",
                    "status": "finished",
                    "download_url": "https://example.com/recording.mp4",
                    "start_time": "2025-01-01T10:00:00Z",
                    "duration": 1800,
                },
            },
        }

        event = DailyCoWebhookEvent(**event_data)
        assert event.type == "recording.ready-to-download"
        assert event.data["recording"]["id"] == "recording-123"
        assert (
            event.data["recording"]["download_url"]
            == "https://example.com/recording.mp4"
        )
