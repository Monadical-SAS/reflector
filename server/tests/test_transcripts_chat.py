"""Tests for transcript chat WebSocket endpoint."""

import asyncio
import threading
import time
from pathlib import Path

import pytest
from httpx_ws import aconnect_ws
from uvicorn import Config, Server

from reflector.db.transcripts import (
    SourceKind,
    TranscriptParticipant,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Word


@pytest.fixture
def chat_appserver(tmpdir, setup_database):
    """Start a real HTTP server for WebSocket testing."""
    from reflector.app import app
    from reflector.db import get_database
    from reflector.settings import settings

    DATA_DIR = settings.DATA_DIR
    settings.DATA_DIR = Path(tmpdir)

    # Start server in separate thread with its own event loop
    host = "127.0.0.1"
    port = 1256  # Different port from rtc tests
    server_started = threading.Event()
    server_exception = None
    server_instance = None

    def run_server():
        nonlocal server_exception, server_instance
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            config = Config(app=app, host=host, port=port, loop=loop)
            server_instance = Server(config)

            async def start_server():
                # Initialize database connection in this event loop
                database = get_database()
                await database.connect()
                try:
                    await server_instance.serve()
                finally:
                    await database.disconnect()

            # Signal that server is starting
            server_started.set()
            loop.run_until_complete(start_server())
        except Exception as e:
            server_exception = e
            server_started.set()
        finally:
            loop.close()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    # Wait for server to start
    server_started.wait(timeout=30)
    if server_exception:
        raise server_exception

    # Wait for server to be fully ready
    time.sleep(1)

    yield server_instance, host, port

    # Stop server
    if server_instance:
        server_instance.should_exit = True
        server_thread.join(timeout=30)

    settings.DATA_DIR = DATA_DIR


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


@pytest.mark.asyncio
async def test_chat_websocket_connection_success(test_transcript, chat_appserver):
    """Test successful WebSocket connection to chat endpoint."""
    server, host, port = chat_appserver
    base_url = f"ws://{host}:{port}/v1"

    async with aconnect_ws(f"{base_url}/transcripts/{test_transcript.id}/chat") as ws:
        # Send unknown message type to test echo behavior
        await ws.send_json({"type": "test", "text": "Hello"})

        # Should receive echo for unknown types
        response = await ws.receive_json()
        assert response["type"] == "echo"
        assert response["data"]["type"] == "test"


@pytest.mark.asyncio
async def test_chat_websocket_nonexistent_transcript(chat_appserver):
    """Test WebSocket connection fails for nonexistent transcript."""
    server, host, port = chat_appserver
    base_url = f"ws://{host}:{port}/v1"

    # Connection should fail or disconnect immediately for non-existent transcript
    # Different behavior from successful connection
    with pytest.raises(Exception):  # Will raise on connection or first operation
        async with aconnect_ws(f"{base_url}/transcripts/nonexistent-id/chat") as ws:
            await ws.send_json({"type": "message", "text": "Hello"})
            await ws.receive_json()


@pytest.mark.asyncio
async def test_chat_websocket_multiple_messages(test_transcript, chat_appserver):
    """Test sending multiple messages through WebSocket."""
    server, host, port = chat_appserver
    base_url = f"ws://{host}:{port}/v1"

    async with aconnect_ws(f"{base_url}/transcripts/{test_transcript.id}/chat") as ws:
        # Send multiple unknown message types (testing echo behavior)
        messages = ["First message", "Second message", "Third message"]

        for i, msg in enumerate(messages):
            await ws.send_json({"type": f"test{i}", "text": msg})
            response = await ws.receive_json()
            assert response["type"] == "echo"
            assert response["data"]["type"] == f"test{i}"
            assert response["data"]["text"] == msg


@pytest.mark.asyncio
async def test_chat_websocket_disconnect_graceful(test_transcript, chat_appserver):
    """Test WebSocket disconnects gracefully."""
    server, host, port = chat_appserver
    base_url = f"ws://{host}:{port}/v1"

    async with aconnect_ws(f"{base_url}/transcripts/{test_transcript.id}/chat") as ws:
        await ws.send_json({"type": "message", "text": "Hello"})
        await ws.receive_json()
        # Close handled by context manager - should not raise


@pytest.mark.asyncio
async def test_chat_websocket_context_generation(
    test_transcript_with_content, chat_appserver
):
    """Test WebVTT context is generated on connection."""
    server, host, port = chat_appserver
    base_url = f"ws://{host}:{port}/v1"

    async with aconnect_ws(
        f"{base_url}/transcripts/{test_transcript_with_content.id}/chat"
    ) as ws:
        # Request context
        await ws.send_json({"type": "get_context"})

        # Receive context response
        response = await ws.receive_json()
        assert response["type"] == "context"
        assert "webvtt" in response

        # Verify WebVTT format
        webvtt = response["webvtt"]
        assert webvtt.startswith("WEBVTT")
        assert "<v Alice>" in webvtt
        assert "<v Bob>" in webvtt
        assert "Hello everyone." in webvtt
        assert "Hi there!" in webvtt


@pytest.mark.asyncio
async def test_chat_websocket_unknown_message_type(test_transcript, chat_appserver):
    """Test unknown message types are echoed back."""
    server, host, port = chat_appserver
    base_url = f"ws://{host}:{port}/v1"

    async with aconnect_ws(f"{base_url}/transcripts/{test_transcript.id}/chat") as ws:
        # Send unknown message type
        await ws.send_json({"type": "unknown", "data": "test"})

        # Should receive echo
        response = await ws.receive_json()
        assert response["type"] == "echo"
        assert response["data"]["type"] == "unknown"
