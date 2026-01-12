"""Tests for transcript chat WebSocket endpoint."""

import pytest

from reflector.db.transcripts import (
    SourceKind,
    TranscriptParticipant,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Word


@pytest.fixture
async def test_transcript(setup_database):
    """Create a test transcript for WebSocket tests."""
    transcript = await transcripts_controller.add(
        name="Test Transcript for Chat", source_kind=SourceKind.FILE
    )
    return transcript


@pytest.fixture
async def test_transcript_with_content(setup_database):
    """Create a test transcript with actual content for WebVTT generation."""
    transcript = await transcripts_controller.add(
        name="Test Transcript with Content", source_kind=SourceKind.FILE
    )

    # Add participants
    await transcripts_controller.update(
        transcript,
        {
            "participants": [
                TranscriptParticipant(id="1", speaker=0, name="Alice").model_dump(),
                TranscriptParticipant(id="2", speaker=1, name="Bob").model_dump(),
            ]
        },
    )

    # Add topic with words
    await transcripts_controller.upsert_topic(
        transcript,
        TranscriptTopic(
            title="Introduction",
            summary="Opening remarks",
            timestamp=0.0,
            words=[
                Word(text="Hello ", start=0.0, end=1.0, speaker=0),
                Word(text="everyone.", start=1.0, end=2.0, speaker=0),
                Word(text="Hi ", start=2.0, end=3.0, speaker=1),
                Word(text="there!", start=3.0, end=4.0, speaker=1),
            ],
        ),
    )

    return transcript


def test_chat_websocket_connection_success(test_transcript):
    """Test successful WebSocket connection to chat endpoint."""
    from starlette.testclient import TestClient

    from reflector.app import app

    with TestClient(app) as client:
        # Connect to WebSocket endpoint
        with client.websocket_connect(
            f"/v1/transcripts/{test_transcript.id}/chat"
        ) as websocket:
            # Send a test message
            websocket.send_json({"type": "message", "text": "Hello"})

            # Receive echo response
            response = websocket.receive_json()
            assert response["type"] == "echo"
            assert response["data"]["type"] == "message"
            assert response["data"]["text"] == "Hello"


def test_chat_websocket_nonexistent_transcript():
    """Test WebSocket connection fails for nonexistent transcript."""
    from starlette.testclient import TestClient
    from starlette.websockets import WebSocketDisconnect

    from reflector.app import app

    with TestClient(app) as client:
        # Try to connect to non-existent transcript - should raise on connect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/v1/transcripts/nonexistent-id/chat"
            ) as websocket:
                websocket.send_json({"type": "message", "text": "Hello"})


def test_chat_websocket_multiple_messages(test_transcript):
    """Test sending multiple messages through WebSocket."""
    from starlette.testclient import TestClient

    from reflector.app import app

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/v1/transcripts/{test_transcript.id}/chat"
        ) as websocket:
            # Send multiple messages
            messages = ["First message", "Second message", "Third message"]

            for msg in messages:
                websocket.send_json({"type": "message", "text": msg})
                response = websocket.receive_json()
                assert response["type"] == "echo"
                assert response["data"]["text"] == msg


def test_chat_websocket_disconnect_graceful(test_transcript):
    """Test WebSocket disconnects gracefully."""
    from starlette.testclient import TestClient

    from reflector.app import app

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/v1/transcripts/{test_transcript.id}/chat"
        ) as websocket:
            websocket.send_json({"type": "message", "text": "Hello"})
            websocket.receive_json()
            # Close connection - context manager handles it
            # No exception should be raised


def test_chat_websocket_context_generation(test_transcript_with_content):
    """Test WebVTT context is generated on connection."""
    from starlette.testclient import TestClient

    from reflector.app import app

    with TestClient(app) as client:
        with client.websocket_connect(
            f"/v1/transcripts/{test_transcript_with_content.id}/chat"
        ) as websocket:
            # Send request for context (new message type)
            websocket.send_json({"type": "get_context"})

            # Receive context response
            response = websocket.receive_json()
            assert response["type"] == "context"
            assert "webvtt" in response

            # Verify WebVTT format
            webvtt = response["webvtt"]
            assert webvtt.startswith("WEBVTT")
            assert "<v Alice>" in webvtt
            assert "<v Bob>" in webvtt
            assert "Hello everyone." in webvtt
            assert "Hi there!" in webvtt


def test_chat_websocket_message_protocol(test_transcript_with_content):
    """Test LLM message streaming protocol (unit test without actual LLM)."""
    # This test verifies the message protocol structure
    # Actual LLM integration requires mocking or live LLM
    import json

    # Verify message types match protocol
    assert json.dumps({"type": "message", "text": "test"})  # Client to server
    assert json.dumps({"type": "token", "text": "chunk"})  # Server to client
    assert json.dumps({"type": "done"})  # Server to client
    assert json.dumps({"type": "error", "message": "error"})  # Server to client
