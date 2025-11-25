#!/usr/bin/env python3
"""
Manual Migration Script: Migrate user_id from Authentik uid to internal user.id

This script should be run manually AFTER applying the database schema migrations.

Usage:
    AUTHENTIK_API_URL=https://your-authentik-url \
    AUTHENTIK_API_TOKEN=your-token \
    DATABASE_URL=postgresql://... \
    python scripts/migrate_user_ids.py

What this script does:
1. Collects all unique UIDs currently used in the database
2. Fetches only those users from Authentik API to populate the users table
3. Updates user_id in: user_api_key, transcript, room, meeting_consent
4. Uses user.uid to lookup the corresponding user.id

The script is idempotent:
- User inserts use ON CONFLICT DO NOTHING (safe if users already exist)
- Update queries only match uid->uuid pairs (no-op if already migrated)
- Safe to run multiple times without side effects

Prerequisites:
- AUTHENTIK_API_URL environment variable must be set
- AUTHENTIK_API_TOKEN environment variable must be set
- DATABASE_URL environment variable must be set
- Authentik API must be accessible
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, create_async_engine

TABLES_WITH_USER_ID = ["user_api_key", "transcript", "room", "meeting_consent"]
NULLABLE_USER_ID_TABLES = {"transcript", "meeting_consent"}
AUTHENTIK_PAGE_SIZE = 100
HTTP_TIMEOUT = 30.0


class AuthentikClient:
    def __init__(self, api_url: str, api_token: str):
        self.api_url = api_url
        self.api_token = api_token

    def _get_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

    async def fetch_all_users(self) -> list[dict[str, Any]]:
        all_users = []
        page = 1

        try:
            async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
                while True:
                    url = f"{self.api_url}/api/v3/core/users/"
                    params = {
                        "page": page,
                        "page_size": AUTHENTIK_PAGE_SIZE,
                        "include_groups": "false",
                    }

                    print(f"  Fetching users from Authentik (page {page})...")
                    response = await client.get(
                        url, headers=self._get_headers(), params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    results = data.get("results", [])
                    if not results:
                        break

                    all_users.extend(results)
                    print(f"  Fetched {len(results)} users from page {page}")

                    if not data.get("next"):
                        break

                    page += 1

            print(f"  Total: {len(all_users)} users fetched from Authentik")
            return all_users

        except httpx.HTTPError as e:
            raise Exception(f"Failed to fetch users from Authentik: {e}") from e


async def collect_used_uids(connection: AsyncConnection) -> set[str]:
    print("\nStep 1: Collecting UIDs from database tables...")
    used_uids = set()

    for table in TABLES_WITH_USER_ID:
        result = await connection.execute(
            text(f'SELECT DISTINCT user_id FROM "{table}" WHERE user_id IS NOT NULL')
        )
        uids = [row[0] for row in result.fetchall()]
        used_uids.update(uids)
        print(f"  Found {len(uids)} unique UIDs in {table}")

    print(f"  Total unique user IDs found: {len(used_uids)}")

    if used_uids:
        sample_id = next(iter(used_uids))
        if len(sample_id) == 36 and sample_id.count("-") == 4:
            print(
                f"\n✅ User IDs are already in UUID format (e.g., {sample_id[:20]}...)"
            )
            print("Migration has already been completed!")
            return set()

    return used_uids


def filter_users_by_uid(
    authentik_users: list[dict[str, Any]], used_uids: set[str]
) -> tuple[list[dict[str, Any]], set[str]]:
    used_authentik_users = [
        user for user in authentik_users if user.get("uid") in used_uids
    ]

    missing_ids = used_uids - {u.get("uid") for u in used_authentik_users}

    print(
        f"  Found {len(used_authentik_users)} matching users in Authentik "
        f"(out of {len(authentik_users)} total)"
    )

    if missing_ids:
        print(
            f"  ⚠ Warning: {len(missing_ids)} UIDs in database not found in Authentik:"
        )
        for user_id in sorted(missing_ids):
            print(f"    - {user_id}")

    return used_authentik_users, missing_ids


async def sync_users_to_database(
    connection: AsyncConnection, authentik_users: list[dict[str, Any]]
) -> tuple[int, int]:
    created = 0
    skipped = 0
    now = datetime.now(timezone.utc)

    for authentik_user in authentik_users:
        user_id = authentik_user["uuid"]
        uid = authentik_user["uid"]
        email = authentik_user.get("email")

        if not email:
            print(f"  ⚠ Skipping user {uid} (no email)")
            skipped += 1
            continue

        result = await connection.execute(
            text("""
                INSERT INTO "user" (id, uid, email, created_at, updated_at)
                VALUES (:id, :uid, :email, :created_at, :updated_at)
                ON CONFLICT (id) DO NOTHING
            """),
            {
                "id": user_id,
                "uid": uid,
                "email": email,
                "created_at": now,
                "updated_at": now,
            },
        )
        if result.rowcount > 0:
            created += 1

    return created, skipped


async def migrate_all_user_ids(connection: AsyncConnection) -> int:
    print("\nStep 3: Migrating user_id columns from uid to internal id...")
    print("(If no rows are updated, migration may have already been completed)")

    total_updated = 0

    for table in TABLES_WITH_USER_ID:
        null_check = (
            f"AND {table}.user_id IS NOT NULL"
            if table in NULLABLE_USER_ID_TABLES
            else ""
        )

        query = f"""
            UPDATE {table}
            SET user_id = u.id
            FROM "user" u
            WHERE {table}.user_id = u.uid
            {null_check}
        """

        print(f"  Updating {table}.user_id...")
        result = await connection.execute(text(query))
        rows = result.rowcount
        print(f"    ✓ Updated {rows} rows")
        total_updated += rows

    return total_updated


async def run_migration(
    database_url: str, authentik_api_url: str, authentik_api_token: str
) -> None:
    engine = create_async_engine(database_url)

    try:
        async with engine.begin() as connection:
            used_uids = await collect_used_uids(connection)
            if not used_uids:
                print("\n⚠️  No user IDs found in database. Nothing to migrate.")
                print("Migration complete (no-op)!")
                return

            print("\nStep 2: Fetching user data from Authentik and syncing users...")
            print("(This script is idempotent - safe to run multiple times)")
            print(f"Authentik API URL: {authentik_api_url}")

            client = AuthentikClient(authentik_api_url, authentik_api_token)
            authentik_users = await client.fetch_all_users()

            if not authentik_users:
                print("\nERROR: No users returned from Authentik API.")
                print(
                    "Please verify your Authentik configuration and ensure users exist."
                )
                sys.exit(1)

            used_authentik_users, _ = filter_users_by_uid(authentik_users, used_uids)
            created, skipped = await sync_users_to_database(
                connection, used_authentik_users
            )

            if created > 0:
                print(f"✓ Created {created} users from Authentik")
            else:
                print("✓ No new users created (users may already exist)")

            if skipped > 0:
                print(f"  ⚠ Skipped {skipped} users without email")

            result = await connection.execute(text('SELECT COUNT(*) FROM "user"'))
            user_count = result.scalar()
            print(f"✓ Users table now has {user_count} users")

            total_updated = await migrate_all_user_ids(connection)

            if total_updated > 0:
                print(f"\n✅ Migration complete! Updated {total_updated} total rows.")
            else:
                print(
                    "\n✅ Migration complete! (No rows updated - migration may have already been completed)"
                )

    except Exception as e:
        print(f"\n❌ ERROR: Migration failed: {e}")
        sys.exit(1)
    finally:
        await engine.dispose()


async def main() -> None:
    database_url = os.getenv("DATABASE_URL")
    authentik_api_url = os.getenv("AUTHENTIK_API_URL")
    authentik_api_token = os.getenv("AUTHENTIK_API_TOKEN")

    if not database_url or not authentik_api_url or not authentik_api_token:
        print(
            "ERROR: DATABASE_URL, AUTHENTIK_API_URL, and AUTHENTIK_API_TOKEN must be set"
        )
        sys.exit(1)

    await run_migration(database_url, authentik_api_url, authentik_api_token)


if __name__ == "__main__":
    asyncio.run(main())
