import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from reflector.api.jibri_webhook import router
from reflector.models import Transcript


@pytest.fixture
def client():
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_db():
    db = Mock(spec=Session)
    db.add = Mock()
    db.commit = Mock()
    db.refresh = Mock()
    return db


@pytest.fixture
def mock_settings():
    with patch("reflector.api.jibri_webhook.settings") as mock:
        mock.JIBRI_RECORDINGS_PATH = "/recordings"
        yield mock


@pytest.fixture
def mock_pipeline():
    with patch("reflector.api.jibri_webhook.TranscriptMainPipeline") as mock:
        pipeline_instance = Mock()
        pipeline_instance.create = Mock()
        mock.return_value = pipeline_instance
        yield mock


class TestJibriWebhook:
    def test_recording_ready_success_with_events(
        self, client, mock_db, mock_settings, mock_pipeline
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.JIBRI_RECORDINGS_PATH = tmpdir

            # Create recording directory and files
            session_id = "test-session-123"
            recording_dir = Path(tmpdir) / session_id
            recording_dir.mkdir()

            recording_file = recording_dir / "recording.mp4"
            recording_file.write_text("fake video content")

            events_file = recording_dir / "events.jsonl"
            events = [
                {
                    "type": "room_created",
                    "timestamp": 1234567890,
                    "room_name": "TestRoom",
                    "room_jid": "testroom@conference.meet.jitsi",
                    "meeting_url": "https://meet.jitsi/TestRoom",
                },
                {
                    "type": "participant_joined",
                    "timestamp": 1234567892,
                    "room_name": "TestRoom",
                    "participant": {
                        "jid": "user1@meet.jitsi/resource",
                        "nick": "John Doe",
                        "id": "user1@meet.jitsi",
                        "is_moderator": False,
                    },
                },
            ]

            with open(events_file, "w") as f:
                for event in events:
                    f.write(json.dumps(event) + "\n")

            # Mock database dependency
            with patch("reflector.api.jibri_webhook.get_db") as mock_get_db:
                mock_get_db.return_value = mock_db

                response = client.post(
                    "/api/v1/jibri/recording-ready",
                    json={
                        "session_id": session_id,
                        "path": session_id,
                        "meeting_url": "https://meet.jitsi/TestRoom",
                    },
                )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "accepted"
            assert data["session_id"] == session_id
            assert data["events_found"] is True
            assert data["participant_count"] == 1

            # Verify transcript was created
            mock_db.add.assert_called_once()
            transcript_arg = mock_db.add.call_args[0][0]
            assert isinstance(transcript_arg, Transcript)
            assert "TestRoom" in transcript_arg.title
            assert transcript_arg.metadata["jitsi"]["room"]["name"] == "TestRoom"

            # Verify pipeline was triggered
            mock_pipeline.return_value.create.assert_called_once()

    def test_recording_ready_success_without_events(
        self, client, mock_db, mock_settings, mock_pipeline
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.JIBRI_RECORDINGS_PATH = tmpdir

            session_id = "test-session-456"
            recording_dir = Path(tmpdir) / session_id
            recording_dir.mkdir()

            recording_file = recording_dir / "recording.mp4"
            recording_file.write_text("fake video content")

            with patch("reflector.api.jibri_webhook.get_db") as mock_get_db:
                mock_get_db.return_value = mock_db

                response = client.post(
                    "/api/v1/jibri/recording-ready",
                    json={
                        "session_id": session_id,
                        "path": session_id,
                        "meeting_url": "https://meet.jitsi/NoEventsRoom",
                    },
                )

            assert response.status_code == 200
            data = response.json()

            assert data["status"] == "accepted"
            assert data["events_found"] is False
            assert data["participant_count"] == 0

            # Verify transcript was created with minimal metadata
            mock_db.add.assert_called_once()
            transcript_arg = mock_db.add.call_args[0][0]
            assert transcript_arg.metadata["jitsi"]["participants"] == []

    def test_recording_ready_path_not_found(self, client, mock_settings):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.JIBRI_RECORDINGS_PATH = tmpdir

            response = client.post(
                "/api/v1/jibri/recording-ready",
                json={
                    "session_id": "nonexistent",
                    "path": "nonexistent",
                    "meeting_url": "https://meet.jitsi/Test",
                },
            )

            assert response.status_code == 404
            assert "Recording path not found" in response.json()["detail"]

    def test_recording_ready_recording_file_not_found(self, client, mock_settings):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.JIBRI_RECORDINGS_PATH = tmpdir

            session_id = "test-no-recording"
            recording_dir = Path(tmpdir) / session_id
            recording_dir.mkdir()

            # No recording.mp4 file created

            response = client.post(
                "/api/v1/jibri/recording-ready",
                json={
                    "session_id": session_id,
                    "path": session_id,
                    "meeting_url": "https://meet.jitsi/Test",
                },
            )

            assert response.status_code == 404
            assert "Recording file not found" in response.json()["detail"]

    def test_recording_ready_with_relative_path(
        self, client, mock_db, mock_settings, mock_pipeline
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.JIBRI_RECORDINGS_PATH = tmpdir

            # Create nested directory structure
            session_id = "2024/01/15/test-session"
            recording_dir = Path(tmpdir) / session_id
            recording_dir.mkdir(parents=True)

            recording_file = recording_dir / "recording.mp4"
            recording_file.write_text("fake video content")

            with patch("reflector.api.jibri_webhook.get_db") as mock_get_db:
                mock_get_db.return_value = mock_db

                response = client.post(
                    "/api/v1/jibri/recording-ready",
                    json={
                        "session_id": "test-session",
                        "path": session_id,  # Relative path with subdirectories
                        "meeting_url": "https://meet.jitsi/Test",
                    },
                )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "accepted"

    def test_recording_ready_empty_meeting_url(
        self, client, mock_db, mock_settings, mock_pipeline
    ):
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings.JIBRI_RECORDINGS_PATH = tmpdir

            session_id = "test-session"
            recording_dir = Path(tmpdir) / session_id
            recording_dir.mkdir()

            recording_file = recording_dir / "recording.mp4"
            recording_file.write_text("fake video content")

            with patch("reflector.api.jibri_webhook.get_db") as mock_get_db:
                mock_get_db.return_value = mock_db

                response = client.post(
                    "/api/v1/jibri/recording-ready",
                    json={
                        "session_id": session_id,
                        "path": session_id,
                        "meeting_url": "",
                    },
                )

            assert response.status_code == 200

            # Verify fallback URL was used
            transcript_arg = mock_db.add.call_args[0][0]
            assert transcript_arg.source_url == f"jitsi://{session_id}"
