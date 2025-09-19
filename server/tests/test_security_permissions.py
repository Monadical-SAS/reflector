import asyncio
import shutil
import threading
import time
from pathlib import Path

import pytest
from httpx_ws import aconnect_ws
from uvicorn import Config, Server

from reflector import zulip as zulip_module
from reflector.app import app
from reflector.db import get_database
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import Room, rooms_controller
from reflector.db.transcripts import (
    SourceKind,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Word
from reflector.settings import settings
from reflector.views.transcripts import create_access_token


@pytest.mark.asyncio
async def test_anonymous_cannot_delete_transcript_in_shared_room(client):
    # Create a shared room with a fake owner id so meeting has a room_id
    room = await rooms_controller.add(
        name="shared-room-test",
        user_id="owner-1",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=True,
        webhook_url="",
        webhook_secret="",
    )

    # Create a meeting for that room (so transcript.meeting_id links to the shared room)
    meeting = await meetings_controller.create(
        id="meeting-sec-test",
        room_name="room-sec-test",
        room_url="room-url",
        host_room_url="host-url",
        start_date=Room.model_fields["created_at"].default_factory(),
        end_date=Room.model_fields["created_at"].default_factory(),
        room=room,
    )

    # Create a transcript owned by someone else and link it to meeting
    t = await transcripts_controller.add(
        name="to-delete",
        source_kind=SourceKind.LIVE,
        user_id="owner-2",
        meeting_id=meeting.id,
        room_id=room.id,
        share_mode="private",
    )

    # Anonymous DELETE should be rejected
    del_resp = await client.delete(f"/transcripts/{t.id}")
    assert del_resp.status_code == 401, del_resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_mutate_participants_on_public_transcript(client):
    # Create a public transcript with no owner
    t = await transcripts_controller.add(
        name="public-transcript",
        source_kind=SourceKind.LIVE,
        user_id=None,
        share_mode="public",
    )

    # Anonymous POST participant must be rejected
    resp = await client.post(
        f"/transcripts/{t.id}/participants",
        json={"name": "AnonUser", "speaker": 0},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_update_and_delete_room(client):
    # Create room as owner id "owner-3" via controller
    room = await rooms_controller.add(
        name="room-anon-update-delete",
        user_id="owner-3",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        webhook_url="",
        webhook_secret="",
    )

    # Anonymous PATCH via API (no auth)
    resp = await client.patch(
        f"/rooms/{room.id}",
        json={
            "name": "room-anon-updated",
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
        },
    )
    # Expect authentication required
    assert resp.status_code == 401, resp.text

    # Anonymous DELETE via API
    del_resp = await client.delete(f"/rooms/{room.id}")
    assert del_resp.status_code == 401, del_resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_post_transcript_to_zulip(client, monkeypatch):
    # Create a public transcript with some content
    t = await transcripts_controller.add(
        name="zulip-public",
        source_kind=SourceKind.LIVE,
        user_id=None,
        share_mode="public",
    )

    # Mock send/update calls
    def _fake_send_message_to_zulip(stream, topic, content):
        return {"id": 12345}

    async def _fake_update_message(message_id, stream, topic, content):
        return {"result": "success"}

    monkeypatch.setattr(
        zulip_module, "send_message_to_zulip", _fake_send_message_to_zulip
    )
    monkeypatch.setattr(zulip_module, "update_zulip_message", _fake_update_message)

    # Anonymous POST to Zulip endpoint
    resp = await client.post(
        f"/transcripts/{t.id}/zulip",
        params={"stream": "general", "topic": "Updates", "include_topics": False},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_assign_speaker_on_public_transcript(client):
    # Create public transcript
    t = await transcripts_controller.add(
        name="public-assign",
        source_kind=SourceKind.LIVE,
        user_id=None,
        share_mode="public",
    )

    # Add a topic with words to be reassigned
    topic = TranscriptTopic(
        title="T1",
        summary="S1",
        timestamp=0.0,
        transcript="Hello",
        words=[Word(start=0.0, end=1.0, text="Hello", speaker=0)],
    )
    transcript = await transcripts_controller.get_by_id(t.id)
    await transcripts_controller.upsert_topic(transcript, topic)

    # Anonymous assign speaker over time range covering the word
    resp = await client.patch(
        f"/transcripts/{t.id}/speaker/assign",
        json={
            "speaker": 1,
            "timestamp_from": 0.0,
            "timestamp_to": 1.0,
        },
    )
    assert resp.status_code == 401, resp.text


# Minimal server fixture for websocket tests
@pytest.fixture
def appserver_ws_simple(setup_database):
    host = "127.0.0.1"
    port = 1256
    server_started = threading.Event()
    server_exception = None
    server_instance = None

    def run_server():
        nonlocal server_exception, server_instance
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            config = Config(app=app, host=host, port=port, loop=loop)
            server_instance = Server(config)

            async def start_server():
                database = get_database()
                await database.connect()
                try:
                    await server_instance.serve()
                finally:
                    await database.disconnect()

            server_started.set()
            loop.run_until_complete(start_server())
        except Exception as e:
            server_exception = e
            server_started.set()
        finally:
            loop.close()

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()

    server_started.wait(timeout=30)
    if server_exception:
        raise server_exception

    time.sleep(0.5)

    yield host, port

    if server_instance:
        server_instance.should_exit = True
        server_thread.join(timeout=30)


@pytest.mark.asyncio
async def test_websocket_denies_anonymous_on_private_transcript(appserver_ws_simple):
    host, port = appserver_ws_simple

    # Create a private transcript owned by someone
    t = await transcripts_controller.add(
        name="private-ws",
        source_kind=SourceKind.LIVE,
        user_id="owner-x",
        share_mode="private",
    )

    base_url = f"http://{host}:{port}/v1"
    # Anonymous connect should be denied
    with pytest.raises(Exception):
        async with aconnect_ws(f"{base_url}/transcripts/{t.id}/events") as ws:
            await ws.close()


@pytest.mark.asyncio
async def test_anonymous_cannot_update_public_transcript(client):
    t = await transcripts_controller.add(
        name="update-me",
        source_kind=SourceKind.LIVE,
        user_id=None,
        share_mode="public",
    )

    resp = await client.patch(
        f"/transcripts/{t.id}",
        json={"title": "New Title From Anonymous"},
    )
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_get_nonshared_room_by_id(client):
    room = await rooms_controller.add(
        name="private-room-exposed",
        user_id="owner-z",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        webhook_url="",
        webhook_secret="",
    )

    resp = await client.get(f"/rooms/{room.id}")
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_call_rooms_webhook_test(client):
    room = await rooms_controller.add(
        name="room-webhook-test",
        user_id="owner-y",
        zulip_auto_post=False,
        zulip_stream="",
        zulip_topic="",
        is_locked=False,
        room_mode="normal",
        recording_type="cloud",
        recording_trigger="automatic-2nd-participant",
        is_shared=False,
        webhook_url="http://localhost.invalid/webhook",
        webhook_secret="secret",
    )

    # Anonymous caller
    resp = await client.post(f"/rooms/{room.id}/webhook/test")
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_anonymous_cannot_create_room(client):
    payload = {
        "name": "room-create-auth-required",
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
    resp = await client.post("/rooms", json=payload)
    assert resp.status_code == 401, resp.text


@pytest.mark.asyncio
async def test_list_search_401_when_public_mode_false(client, monkeypatch):
    monkeypatch.setattr(settings, "PUBLIC_MODE", False)

    resp = await client.get("/transcripts")
    assert resp.status_code == 401

    resp = await client.get("/transcripts/search", params={"q": "hello"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_audio_mp3_requires_token_for_owned_transcript(
    client, tmpdir, monkeypatch
):
    # Use temp data dir
    monkeypatch.setattr(settings, "DATA_DIR", Path(tmpdir).as_posix())

    # Create owner transcript and attach a local mp3
    t = await transcripts_controller.add(
        name="owned-audio",
        source_kind=SourceKind.LIVE,
        user_id="owner-a",
        share_mode="private",
    )

    tr = await transcripts_controller.get_by_id(t.id)
    await transcripts_controller.update(tr, {"status": "ended"})

    # copy fixture audio to transcript path
    audio_path = Path(__file__).parent / "records" / "test_mathieu_hello.mp3"
    tr.audio_mp3_filename.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(audio_path, tr.audio_mp3_filename)

    # Anonymous GET without token should be 403 or 404 depending on access; we call mp3
    resp = await client.get(f"/transcripts/{t.id}/audio/mp3")
    assert resp.status_code == 403

    # With token should succeed
    token = create_access_token(
        {"sub": tr.user_id}, expires_delta=__import__("datetime").timedelta(minutes=15)
    )
    resp2 = await client.get(f"/transcripts/{t.id}/audio/mp3", params={"token": token})
    assert resp2.status_code == 200
