"""Tests for the password auth backend."""

import pytest
from httpx import AsyncClient
from jose import jwt

from reflector.auth.password_utils import hash_password
from reflector.settings import settings


@pytest.fixture
async def password_app():
    """Create a minimal FastAPI app with the password auth router."""
    from fastapi import FastAPI

    from reflector.auth import auth_password

    app = FastAPI()
    app.include_router(auth_password.router, prefix="/v1")
    # Reset rate limiter between tests
    auth_password._login_attempts.clear()
    return app


@pytest.fixture
async def password_client(password_app):
    """Create a test client for the password auth app."""
    async with AsyncClient(app=password_app, base_url="http://test/v1") as client:
        yield client


async def _create_user_with_password(email: str, password: str):
    """Helper to create a user with a password hash in the DB."""
    from reflector.db.users import user_controller
    from reflector.utils import generate_uuid4

    pw_hash = hash_password(password)
    return await user_controller.create_or_update(
        id=generate_uuid4(),
        authentik_uid=f"local:{email}",
        email=email,
        password_hash=pw_hash,
    )


@pytest.mark.asyncio
async def test_login_success(password_client, setup_database):
    await _create_user_with_password("admin@test.com", "testpass123")

    response = await password_client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "testpass123"},
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0

    # Verify the JWT is valid
    payload = jwt.decode(
        data["access_token"],
        settings.SECRET_KEY,
        algorithms=["HS256"],
    )
    assert payload["email"] == "admin@test.com"
    assert "sub" in payload
    assert "exp" in payload


@pytest.mark.asyncio
async def test_login_wrong_password(password_client, setup_database):
    await _create_user_with_password("user@test.com", "correctpassword")

    response = await password_client.post(
        "/auth/login",
        json={"email": "user@test.com", "password": "wrongpassword"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(password_client, setup_database):
    response = await password_client.post(
        "/auth/login",
        json={"email": "nobody@test.com", "password": "anything"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_user_without_password_hash(password_client, setup_database):
    """User exists but has no password_hash (e.g. Authentik user)."""
    from reflector.db.users import user_controller
    from reflector.utils import generate_uuid4

    await user_controller.create_or_update(
        id=generate_uuid4(),
        authentik_uid="authentik:abc123",
        email="oidc@test.com",
    )

    response = await password_client.post(
        "/auth/login",
        json={"email": "oidc@test.com", "password": "anything"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_rate_limiting(password_client, setup_database):
    from reflector.auth import auth_password

    # Reset rate limiter
    auth_password._login_attempts.clear()

    for _ in range(10):
        await password_client.post(
            "/auth/login",
            json={"email": "fake@test.com", "password": "wrong"},
        )

    # 11th attempt should be rate-limited
    response = await password_client.post(
        "/auth/login",
        json={"email": "fake@test.com", "password": "wrong"},
    )

    assert response.status_code == 429


@pytest.mark.asyncio
async def test_jwt_create_and_verify():
    from reflector.auth.auth_password import _create_access_token, _verify_token

    token, expires_in = _create_access_token("user-123", "test@example.com")
    assert expires_in > 0

    payload = _verify_token(token)
    assert payload["sub"] == "user-123"
    assert payload["email"] == "test@example.com"
    assert "exp" in payload


@pytest.mark.asyncio
async def test_authenticate_user_with_jwt():
    from reflector.auth.auth_password import (
        _authenticate_user,
        _create_access_token,
    )

    token, _ = _create_access_token("user-abc", "abc@test.com")
    user = await _authenticate_user(token, None)

    assert user is not None
    assert user.sub == "user-abc"
    assert user.email == "abc@test.com"


@pytest.mark.asyncio
async def test_authenticate_user_invalid_jwt():
    from fastapi import HTTPException

    from reflector.auth.auth_password import _authenticate_user

    with pytest.raises(HTTPException) as exc_info:
        await _authenticate_user("invalid.jwt.token", None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_authenticate_user_no_credentials():
    from reflector.auth.auth_password import _authenticate_user

    user = await _authenticate_user(None, None)
    assert user is None


@pytest.mark.asyncio
async def test_current_user_raises_without_token():
    """Verify that current_user dependency raises 401 without token."""
    from fastapi import Depends, FastAPI
    from fastapi.testclient import TestClient

    from reflector.auth import auth_password

    app = FastAPI()

    @app.get("/test")
    async def test_endpoint(user=Depends(auth_password.current_user)):
        return {"user": user.sub}

    # Use sync TestClient for simplicity
    client = TestClient(app)
    response = client.get("/test")
    # OAuth2PasswordBearer with auto_error=False returns None, then current_user raises 401
    assert response.status_code == 401
