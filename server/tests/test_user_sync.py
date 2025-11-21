from unittest.mock import patch

import pytest

from reflector.db.users import user_controller
from reflector.worker.user_sync import (
    AuthentikUser,
    sync_users_to_database,
)


@pytest.fixture
def mock_authentik_users() -> list[AuthentikUser]:
    """Sample Authentik users for testing."""
    return [
        {
            "uuid": "user-uuid-1",
            "uid": "user-uid-1",
            "email": "user1@example.com",
        },
        {
            "uuid": "user-uuid-2",
            "uid": "user-uid-2",
            "email": "user2@example.com",
        },
        {
            "uuid": "user-uuid-3",
            "uid": "user-uid-3",
            "email": None,  # User without email
        },
    ]


@pytest.mark.asyncio
async def test_sync_users_to_database_creates_new_users(mock_authentik_users):
    """Test that new users are created successfully."""
    stats = await sync_users_to_database(mock_authentik_users)

    assert stats["created"] == 2
    assert stats["updated"] == 0
    assert stats["skipped"] == 1  # User without email
    assert stats["errors"] == 0

    # Verify users were created
    user1 = await user_controller.get_by_uid("user-uid-1")
    assert user1 is not None
    assert user1.id == "user-uuid-1"
    assert user1.email == "user1@example.com"

    user2 = await user_controller.get_by_uid("user-uid-2")
    assert user2 is not None
    assert user2.id == "user-uuid-2"
    assert user2.email == "user2@example.com"


@pytest.mark.asyncio
async def test_sync_users_to_database_updates_existing_users():
    """Test that existing users are updated when email changes."""
    # Create initial user
    initial_users: list[AuthentikUser] = [
        {
            "uuid": "user-uuid-4",
            "uid": "user-uid-4",
            "email": "old-email@example.com",
        }
    ]
    await sync_users_to_database(initial_users)

    # Update with new email
    updated_users: list[AuthentikUser] = [
        {
            "uuid": "user-uuid-4",
            "uid": "user-uid-4",
            "email": "new-email@example.com",
        }
    ]
    stats = await sync_users_to_database(updated_users)

    assert stats["created"] == 0
    assert stats["updated"] == 1
    assert stats["skipped"] == 0
    assert stats["errors"] == 0

    # Verify email was updated
    user = await user_controller.get_by_uid("user-uid-4")
    assert user.email == "new-email@example.com"


@pytest.mark.asyncio
async def test_sync_users_to_database_skips_unchanged_users():
    """Test that unchanged users are skipped."""
    # Create initial user
    initial_users: list[AuthentikUser] = [
        {
            "uuid": "user-uuid-5",
            "uid": "user-uid-5",
            "email": "unchanged@example.com",
        }
    ]
    await sync_users_to_database(initial_users)

    # Sync same user again
    stats = await sync_users_to_database(initial_users)

    assert stats["created"] == 0
    assert stats["updated"] == 0
    assert stats["skipped"] == 1
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_sync_users_to_database_skips_users_without_email(mock_authentik_users):
    """Test that users without email are skipped."""
    users_without_email: list[AuthentikUser] = [mock_authentik_users[2]]
    stats = await sync_users_to_database(users_without_email)

    assert stats["created"] == 0
    assert stats["updated"] == 0
    assert stats["skipped"] == 1
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_sync_users_to_database_handles_database_errors():
    """Test that database errors are caught and counted."""
    error_users: list[AuthentikUser] = [
        {
            "uuid": "user-uuid-6",
            "uid": "user-uid-6",
            "email": "error@example.com",
        }
    ]

    with patch(
        "reflector.worker.user_sync.user_controller.create_or_update",
        side_effect=Exception("Database error"),
    ):
        stats = await sync_users_to_database(error_users)

    assert stats["created"] == 0
    assert stats["updated"] == 0
    assert stats["skipped"] == 0
    assert stats["errors"] == 1


@pytest.mark.asyncio
async def test_sync_users_mixed_operations():
    """Test sync with mixed operations: create, update, skip."""
    # Create some initial users
    initial_users: list[AuthentikUser] = [
        {
            "uuid": "user-uuid-8",
            "uid": "user-uid-8",
            "email": "existing@example.com",
        }
    ]
    await sync_users_to_database(initial_users)

    # Sync with mix of new, updated, and unchanged users
    mixed_users: list[AuthentikUser] = [
        # Existing user with same email (skip)
        {
            "uuid": "user-uuid-8",
            "uid": "user-uid-8",
            "email": "existing@example.com",
        },
        # Existing user with new email (update)
        {
            "uuid": "user-uuid-8",
            "uid": "user-uid-8",
            "email": "updated@example.com",
        },
        # New user (create)
        {
            "uuid": "user-uuid-9",
            "uid": "user-uid-9",
            "email": "new@example.com",
        },
        # User without email (skip)
        {
            "uuid": "user-uuid-10",
            "uid": "user-uid-10",
            "email": None,
        },
    ]

    stats = await sync_users_to_database(mixed_users)

    assert stats["created"] == 1  # New user
    assert stats["updated"] == 1  # Email changed
    assert stats["skipped"] == 2  # Unchanged + no email
    assert stats["errors"] == 0


@pytest.mark.asyncio
async def test_user_controller_get_by_uid_not_found():
    """Test that get_by_uid returns None for non-existent users."""
    user = await user_controller.get_by_uid("non-existent-uid")
    assert user is None


@pytest.mark.asyncio
async def test_user_controller_get_by_email():
    """Test getting user by email."""
    test_user: AuthentikUser = {
        "uuid": "user-uuid-11",
        "uid": "user-uid-11",
        "email": "find-by-email@example.com",
    }
    await sync_users_to_database([test_user])

    user = await user_controller.get_by_email("find-by-email@example.com")
    assert user is not None
    assert user.uid == "user-uid-11"


@pytest.mark.asyncio
async def test_user_controller_list_all():
    """Test listing all users."""
    test_users: list[AuthentikUser] = [
        {
            "uuid": "user-uuid-12",
            "uid": "user-uid-12",
            "email": "list-test-1@example.com",
        },
        {
            "uuid": "user-uuid-13",
            "uid": "user-uid-13",
            "email": "list-test-2@example.com",
        },
    ]
    await sync_users_to_database(test_users)

    all_users = await user_controller.list_all()
    assert len(all_users) >= 2

    uids = {u.uid for u in all_users}
    assert "user-uid-12" in uids
    assert "user-uid-13" in uids
