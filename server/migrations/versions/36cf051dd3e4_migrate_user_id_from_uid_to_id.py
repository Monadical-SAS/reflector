"""migrate_user_id_from_uid_to_id

Revision ID: 36cf051dd3e4
Revises: bbafedfa510c
Create Date: 2025-11-20 14:34:54.941338

"""

import asyncio
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from reflector.authentik_client import authentik_client
from reflector.settings import settings

# revision identifiers, used by Alembic.
revision: str = "36cf051dd3e4"
down_revision: Union[str, None] = "bbafedfa510c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Migrate user_id columns from Authentik uid to our internal user.id.

    This migration:
    1. Checks if there's existing data that needs migration
    2. If no data exists and Authentik is not configured, safely skips (for CI/test environments)
    3. If data exists, syncs users from Authentik API to populate the users table
    4. Updates user_id in: user_api_key, transcript, room, meeting_consent
    5. Uses user.uid to lookup the corresponding user.id

    Prerequisites (only when migrating existing data):
    - AUTHENTIK_API_URL and AUTHENTIK_API_TOKEN must be configured
    - Authentik API must be accessible
    """
    connection = op.get_bind()

    # Check if there's any existing data that would need migration
    tables_to_check = ["user_api_key", "transcript", "room", "meeting_consent"]
    has_existing_data = False

    for table in tables_to_check:
        result = connection.execute(sa.text(f'SELECT COUNT(*) FROM "{table}"'))
        count = result.scalar()
        if count > 0:
            print(f"Found {count} existing records in {table}")
            has_existing_data = True

    # If no Authentik credentials, check if we can skip the migration
    if not settings.AUTHENTIK_API_URL or not settings.AUTHENTIK_API_TOKEN:
        if not has_existing_data:
            print(
                "⚠️  Authentik credentials not configured, but no existing data to migrate."
            )
            print("Skipping Authentik user sync (clean database).")
            print("Migration complete (no-op)!")
            return
        else:
            raise Exception(
                "Cannot migrate: AUTHENTIK_API_URL and AUTHENTIK_API_TOKEN must be "
                "configured to migrate existing user data. "
                "Please set these environment variables and try again."
            )

    print("Step 1: Syncing users from Authentik...")
    print(f"Authentik API URL: {settings.AUTHENTIK_API_URL}")

    async def sync_from_authentik():
        try:
            authentik_users = await authentik_client.get_all_users()

            if not authentik_users:
                raise Exception(
                    "No users returned from Authentik API. Please verify your "
                    "Authentik configuration and ensure users exist."
                )

            created = 0
            skipped = 0
            now = datetime.now(timezone.utc)

            for authentik_user in authentik_users:
                user_id = authentik_user["uuid"]
                uid = authentik_user["uid"]
                email = authentik_user.get("email")

                if not email:
                    skipped += 1
                    continue

                connection.execute(
                    sa.text("""
                        INSERT INTO "user" (id, uid, email, created_at, updated_at)
                        VALUES (:id, :uid, :email, :created_at, :updated_at)
                    """),
                    {
                        "id": user_id,
                        "uid": uid,
                        "email": email,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                created += 1

            print(f"✓ Created {created} users from Authentik")
            if skipped > 0:
                print(f"  ⚠ Skipped {skipped} users without email")

            return True

        except Exception as e:
            raise Exception(f"Failed to sync users from Authentik: {e}")

    asyncio.run(sync_from_authentik())

    result = connection.execute(sa.text('SELECT COUNT(*) FROM "user"'))
    user_count = result.scalar()

    if user_count == 0:
        raise Exception(
            "Cannot proceed with migration: users table is still empty after sync. "
            "Please verify Authentik configuration and try again."
        )

    print(f"✓ Users table now has {user_count} users")
    print(f"\nStep 2: Migrating user_id columns from uid to internal id...")

    print("Updating user_api_key.user_id...")
    connection.execute(
        sa.text("""
        UPDATE user_api_key
        SET user_id = u.id
        FROM "user" u
        WHERE user_api_key.user_id = u.uid
    """)
    )

    print("Updating transcript.user_id...")
    connection.execute(
        sa.text("""
        UPDATE transcript
        SET user_id = u.id
        FROM "user" u
        WHERE transcript.user_id = u.uid
        AND transcript.user_id IS NOT NULL
    """)
    )

    print("Updating room.user_id...")
    connection.execute(
        sa.text("""
        UPDATE room
        SET user_id = u.id
        FROM "user" u
        WHERE room.user_id = u.uid
    """)
    )

    print("Updating meeting_consent.user_id...")
    connection.execute(
        sa.text("""
        UPDATE meeting_consent
        SET user_id = u.id
        FROM "user" u
        WHERE meeting_consent.user_id = u.uid
        AND meeting_consent.user_id IS NOT NULL
    """)
    )

    print("Migration complete!")


def downgrade() -> None:
    """
    Revert user_id columns from internal user.id back to Authentik uid.
    Delete all users from user table (it was empty before migration).
    """
    connection = op.get_bind()

    print("Reverting user_id columns back to Authentik uid...")

    connection.execute(
        sa.text("""
        UPDATE user_api_key
        SET user_id = u.uid
        FROM "user" u
        WHERE user_api_key.user_id = u.id
    """)
    )

    connection.execute(
        sa.text("""
        UPDATE transcript
        SET user_id = u.uid
        FROM "user" u
        WHERE transcript.user_id = u.id
        AND transcript.user_id IS NOT NULL
    """)
    )

    connection.execute(
        sa.text("""
        UPDATE room
        SET user_id = u.uid
        FROM "user" u
        WHERE room.user_id = u.id
    """)
    )

    connection.execute(
        sa.text("""
        UPDATE meeting_consent
        SET user_id = u.uid
        FROM "user" u
        WHERE meeting_consent.user_id = u.id
        AND meeting_consent.user_id IS NOT NULL
    """)
    )

    print("Deleting all users from user table...")
    connection.execute(sa.text('DELETE FROM "user"'))

    print("✓ Downgrade complete")
