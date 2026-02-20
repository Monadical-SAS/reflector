"""Tests for admin user creation logic (used by create_admin CLI tool)."""

import pytest

from reflector.auth.password_utils import hash_password, verify_password
from reflector.db.users import user_controller
from reflector.utils import generate_uuid4


async def _provision_admin(email: str, password: str):
    """Mirrors the logic in create_admin.create_admin() without managing DB connections."""
    password_hash = hash_password(password)

    existing = await user_controller.get_by_email(email)
    if existing:
        await user_controller.set_password_hash(existing.id, password_hash)
    else:
        await user_controller.create_or_update(
            id=generate_uuid4(),
            authentik_uid=f"local:{email}",
            email=email,
            password_hash=password_hash,
        )


@pytest.mark.asyncio
async def test_create_admin_new_user(setup_database):
    await _provision_admin("newadmin@test.com", "password123")

    user = await user_controller.get_by_email("newadmin@test.com")
    assert user is not None
    assert user.email == "newadmin@test.com"
    assert user.authentik_uid == "local:newadmin@test.com"
    assert user.password_hash is not None
    assert verify_password("password123", user.password_hash)


@pytest.mark.asyncio
async def test_create_admin_updates_existing(setup_database):
    # Create first
    await _provision_admin("admin@test.com", "oldpassword")
    user1 = await user_controller.get_by_email("admin@test.com")

    # Update password
    await _provision_admin("admin@test.com", "newpassword")
    user2 = await user_controller.get_by_email("admin@test.com")

    assert user1.id == user2.id  # same user, not duplicated
    assert verify_password("newpassword", user2.password_hash)
    assert not verify_password("oldpassword", user2.password_hash)


@pytest.mark.asyncio
async def test_create_admin_idempotent(setup_database):
    await _provision_admin("admin@test.com", "samepassword")
    await _provision_admin("admin@test.com", "samepassword")

    # Should only have one user
    users = await user_controller.list_all()
    admin_users = [u for u in users if u.email == "admin@test.com"]
    assert len(admin_users) == 1


@pytest.mark.asyncio
async def test_create_or_update_with_password_hash(setup_database):
    """Test the extended create_or_update method with password_hash parameter."""
    pw_hash = hash_password("test123")
    user = await user_controller.create_or_update(
        id=generate_uuid4(),
        authentik_uid="local:test@example.com",
        email="test@example.com",
        password_hash=pw_hash,
    )

    assert user.password_hash == pw_hash

    fetched = await user_controller.get_by_email("test@example.com")
    assert fetched is not None
    assert verify_password("test123", fetched.password_hash)


@pytest.mark.asyncio
async def test_set_password_hash(setup_database):
    """Test the set_password_hash method."""
    user = await user_controller.create_or_update(
        id=generate_uuid4(),
        authentik_uid="local:pw@test.com",
        email="pw@test.com",
    )
    assert user.password_hash is None

    pw_hash = hash_password("newpass")
    await user_controller.set_password_hash(user.id, pw_hash)

    updated = await user_controller.get_by_email("pw@test.com")
    assert updated is not None
    assert verify_password("newpass", updated.password_hash)
