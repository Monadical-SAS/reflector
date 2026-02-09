"""WebSocket broadcast delivery tests for STATUS and DAG_STATUS events.

Tests the full chain identified in DEBUG.md:
  broadcast_event() → ws_manager.send_json() → Redis/in-memory pub/sub
    → _pubsub_data_reader() → socket.send_json() → WebSocket client

Covers:
1. STATUS event delivery to transcript room WS
2. DAG_STATUS event delivery to transcript room WS
3. Full broadcast_event() chain (requires broadcast.py patching)
4. _pubsub_data_reader resilience when a client disconnects
"""

import asyncio
import threading
import time

import pytest
from httpx import AsyncClient
from httpx_ws import aconnect_ws
from uvicorn import Config, Server


@pytest.fixture
def appserver_ws_broadcast(setup_database, monkeypatch):
    """Start real uvicorn server for WebSocket broadcast tests.

    Also patches broadcast.py's get_ws_manager (missing from conftest autouse fixture).
    """
    # Patch broadcast.py's get_ws_manager — conftest.py misses this module.
    # Without this, broadcast_event() creates a real Redis ws_manager.
    import reflector.ws_manager as ws_mod
    from reflector.app import app
    from reflector.db import get_database

    monkeypatch.setattr(
        "reflector.hatchet.broadcast.get_ws_manager", ws_mod.get_ws_manager
    )

    host = "127.0.0.1"
    port = 1259
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
        server_thread.join(timeout=2.0)

    from reflector.ws_manager import reset_ws_manager

    reset_ws_manager()


async def _create_transcript(host: str, port: int, name: str) -> str:
    """Create a transcript via ASGI transport and return its ID."""
    from reflector.app import app

    async with AsyncClient(app=app, base_url=f"http://{host}:{port}/v1") as ac:
        resp = await ac.post("/transcripts", json={"name": name})
        assert resp.status_code == 200, f"Failed to create transcript: {resp.text}"
        return resp.json()["id"]


async def _drain_historical_events(ws, timeout: float = 0.5) -> list[dict]:
    """Read all historical events sent on WS connect (non-blocking drain)."""
    events = []
    deadline = asyncio.get_event_loop().time() + timeout
    while asyncio.get_event_loop().time() < deadline:
        try:
            msg = await asyncio.wait_for(ws.receive_json(), timeout=0.1)
            events.append(msg)
        except (asyncio.TimeoutError, Exception):
            break
    return events


# ---------------------------------------------------------------------------
# Test 1: STATUS event delivery via ws_manager.send_json
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_transcript_ws_receives_status_via_send_json(appserver_ws_broadcast):
    """STATUS event published via ws_manager.send_json() arrives at transcript room WS."""
    host, port = appserver_ws_broadcast
    transcript_id = await _create_transcript(host, port, "Status send_json test")

    ws_url = f"http://{host}:{port}/v1/transcripts/{transcript_id}/events"
    async with aconnect_ws(ws_url) as ws:
        await _drain_historical_events(ws)

        import reflector.ws_manager as ws_mod

        ws_manager = ws_mod.get_ws_manager()
        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message={"event": "STATUS", "data": {"value": "processing"}},
        )

        msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        assert msg["event"] == "STATUS"
        assert msg["data"]["value"] == "processing"


# ---------------------------------------------------------------------------
# Test 2: DAG_STATUS event delivery via ws_manager.send_json
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_transcript_ws_receives_dag_status_via_send_json(appserver_ws_broadcast):
    """DAG_STATUS event published via ws_manager.send_json() arrives at transcript room WS."""
    host, port = appserver_ws_broadcast
    transcript_id = await _create_transcript(host, port, "DAG_STATUS send_json test")

    dag_payload = {
        "event": "DAG_STATUS",
        "data": {
            "workflow_run_id": "test-run-123",
            "tasks": [
                {
                    "name": "get_recording",
                    "status": "completed",
                    "started_at": "2025-01-01T00:00:00Z",
                    "finished_at": "2025-01-01T00:00:05Z",
                    "duration_seconds": 5.0,
                    "parents": [],
                    "error": None,
                    "children_total": None,
                    "children_completed": None,
                    "progress_pct": None,
                },
                {
                    "name": "process_tracks",
                    "status": "running",
                    "started_at": "2025-01-01T00:00:05Z",
                    "finished_at": None,
                    "duration_seconds": None,
                    "parents": ["get_recording"],
                    "error": None,
                    "children_total": 3,
                    "children_completed": 1,
                    "progress_pct": 33.3,
                },
            ],
        },
    }

    ws_url = f"http://{host}:{port}/v1/transcripts/{transcript_id}/events"
    async with aconnect_ws(ws_url) as ws:
        await _drain_historical_events(ws)

        import reflector.ws_manager as ws_mod

        ws_manager = ws_mod.get_ws_manager()
        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message=dag_payload,
        )

        msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        assert msg["event"] == "DAG_STATUS"
        assert msg["data"]["workflow_run_id"] == "test-run-123"
        assert len(msg["data"]["tasks"]) == 2
        assert msg["data"]["tasks"][0]["name"] == "get_recording"
        assert msg["data"]["tasks"][0]["status"] == "completed"
        assert msg["data"]["tasks"][1]["name"] == "process_tracks"
        assert msg["data"]["tasks"][1]["children_completed"] == 1


# ---------------------------------------------------------------------------
# Test 3: Full broadcast_event() chain for STATUS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_broadcast_event_delivers_status_to_transcript_ws(appserver_ws_broadcast):
    """broadcast_event() end-to-end: STATUS event reaches transcript room WS."""
    host, port = appserver_ws_broadcast
    transcript_id = await _create_transcript(host, port, "broadcast_event STATUS test")

    ws_url = f"http://{host}:{port}/v1/transcripts/{transcript_id}/events"
    async with aconnect_ws(ws_url) as ws:
        await _drain_historical_events(ws)

        from reflector.db.transcripts import TranscriptEvent
        from reflector.hatchet.broadcast import broadcast_event
        from reflector.logger import logger

        log = logger.bind(transcript_id=transcript_id)
        event = TranscriptEvent(event="STATUS", data={"value": "processing"})
        await broadcast_event(transcript_id, event, logger=log)

        msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        assert msg["event"] == "STATUS"
        assert msg["data"]["value"] == "processing"


# ---------------------------------------------------------------------------
# Test 4: Full broadcast_event() chain for DAG_STATUS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_broadcast_event_delivers_dag_status_to_transcript_ws(
    appserver_ws_broadcast,
):
    """broadcast_event() end-to-end: DAG_STATUS event reaches transcript room WS."""
    host, port = appserver_ws_broadcast
    transcript_id = await _create_transcript(host, port, "broadcast_event DAG test")

    ws_url = f"http://{host}:{port}/v1/transcripts/{transcript_id}/events"
    async with aconnect_ws(ws_url) as ws:
        await _drain_historical_events(ws)

        from reflector.db.transcripts import TranscriptEvent
        from reflector.hatchet.broadcast import broadcast_event
        from reflector.logger import logger

        log = logger.bind(transcript_id=transcript_id)
        event = TranscriptEvent(
            event="DAG_STATUS",
            data={
                "workflow_run_id": "test-run-456",
                "tasks": [
                    {
                        "name": "get_recording",
                        "status": "running",
                        "started_at": None,
                        "finished_at": None,
                        "duration_seconds": None,
                        "parents": [],
                        "error": None,
                        "children_total": None,
                        "children_completed": None,
                        "progress_pct": None,
                    }
                ],
            },
        )
        await broadcast_event(transcript_id, event, logger=log)

        msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
        assert msg["event"] == "DAG_STATUS"
        assert msg["data"]["tasks"][0]["name"] == "get_recording"


# ---------------------------------------------------------------------------
# Test 5: Multiple rapid events arrive in order
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_multiple_events_arrive_in_order(appserver_ws_broadcast):
    """Multiple STATUS then DAG_STATUS events arrive in correct order."""
    host, port = appserver_ws_broadcast
    transcript_id = await _create_transcript(host, port, "ordering test")

    ws_url = f"http://{host}:{port}/v1/transcripts/{transcript_id}/events"
    async with aconnect_ws(ws_url) as ws:
        await _drain_historical_events(ws)

        import reflector.ws_manager as ws_mod

        ws_manager = ws_mod.get_ws_manager()

        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message={"event": "STATUS", "data": {"value": "processing"}},
        )
        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message={
                "event": "DAG_STATUS",
                "data": {"workflow_run_id": "r1", "tasks": []},
            },
        )
        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message={
                "event": "DAG_STATUS",
                "data": {
                    "workflow_run_id": "r1",
                    "tasks": [{"name": "a", "status": "running"}],
                },
            },
        )
        await ws_manager.send_json(
            room_id=f"ts:{transcript_id}",
            message={"event": "STATUS", "data": {"value": "ended"}},
        )

        msgs = []
        for _ in range(4):
            msg = await asyncio.wait_for(ws.receive_json(), timeout=5.0)
            msgs.append(msg)

        assert msgs[0]["event"] == "STATUS"
        assert msgs[0]["data"]["value"] == "processing"
        assert msgs[1]["event"] == "DAG_STATUS"
        assert msgs[1]["data"]["tasks"] == []
        assert msgs[2]["event"] == "DAG_STATUS"
        assert len(msgs[2]["data"]["tasks"]) == 1
        assert msgs[3]["event"] == "STATUS"
        assert msgs[3]["data"]["value"] == "ended"
