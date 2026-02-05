import asyncio
import threading
import time

import pytest
from httpx_ws import aconnect_ws
from uvicorn import Config, Server


@pytest.fixture
def appserver_ws_user(setup_database):
    from reflector.app import app
    from reflector.db import get_database

    host = "127.0.0.1"
    port = 1257
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

    # Reset global singleton for test isolation
    from reflector.ws_manager import reset_ws_manager

    reset_ws_manager()


@pytest.fixture(autouse=True)
def patch_jwt_verification(monkeypatch):
    """Patch JWT verification to accept HS256 tokens signed with SECRET_KEY for tests."""
    from jose import jwt

    from reflector.settings import settings

    def _verify_token(self, token: str):
        # Do not validate audience in tests
        return jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])  # type: ignore[arg-type]

    monkeypatch.setattr(
        "reflector.auth.auth_jwt.JWTAuth.verify_token", _verify_token, raising=True
    )


def _make_dummy_jwt(sub: str = "user123") -> str:
    # Create a short HS256 JWT using the app secret to pass verification in tests
    from datetime import datetime, timedelta, timezone

    from jose import jwt

    from reflector.settings import settings

    payload = {
        "sub": sub,
        "email": f"{sub}@example.com",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
    }
    # Note: production uses RS256 public key verification; tests can sign with SECRET_KEY
    return jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")


@pytest.mark.asyncio
async def test_user_ws_rejects_missing_subprotocol(appserver_ws_user):
    host, port = appserver_ws_user
    base_ws = f"http://{host}:{port}/v1/events"
    # No subprotocol/header with token
    with pytest.raises(Exception):
        async with aconnect_ws(base_ws) as ws:  # type: ignore
            # Should close during handshake; if not, close explicitly
            await ws.close()


@pytest.mark.asyncio
async def test_user_ws_rejects_invalid_token(appserver_ws_user):
    host, port = appserver_ws_user
    base_ws = f"http://{host}:{port}/v1/events"

    # Send wrong token via WebSocket subprotocols
    protocols = ["bearer", "totally-invalid-token"]
    with pytest.raises(Exception):
        async with aconnect_ws(base_ws, subprotocols=protocols) as ws:  # type: ignore
            await ws.close()


@pytest.mark.asyncio
async def test_user_ws_accepts_valid_token_and_receives_events(appserver_ws_user):
    host, port = appserver_ws_user
    base_ws = f"http://{host}:{port}/v1/events"

    # Create a test user in the database
    from reflector.db.users import user_controller

    test_uid = "user-abc"
    user = await user_controller.create_or_update(
        id="test-user-id-abc", authentik_uid=test_uid, email="user-abc@example.com"
    )

    token = _make_dummy_jwt(test_uid)
    subprotocols = ["bearer", token]

    # Connect and then trigger an event via HTTP create
    async with aconnect_ws(base_ws, subprotocols=subprotocols) as ws:
        await asyncio.sleep(0.2)

        # Emit an event to the user's room via a standard HTTP action
        from httpx import AsyncClient

        from reflector.app import app
        from reflector.auth import current_user, current_user_optional

        # Override auth dependencies so HTTP request is performed as the same user
        # Use the internal user.id (not the Authentik UID)
        app.dependency_overrides[current_user] = lambda: {
            "sub": user.id,
            "email": "user-abc@example.com",
        }
        app.dependency_overrides[current_user_optional] = lambda: {
            "sub": user.id,
            "email": "user-abc@example.com",
        }

        # Use in-memory client (global singleton makes it share ws_manager)
        async with AsyncClient(app=app, base_url=f"http://{host}:{port}/v1") as ac:
            # Create a transcript as this user so that the server publishes TRANSCRIPT_CREATED to user room
            resp = await ac.post("/transcripts", json={"name": "WS Test"})
            assert resp.status_code == 200

        # Receive the published event
        msg = await ws.receive_json()
        assert msg["event"] == "TRANSCRIPT_CREATED"
        assert "id" in msg["data"]

        # Clean overrides
        del app.dependency_overrides[current_user]
        del app.dependency_overrides[current_user_optional]
