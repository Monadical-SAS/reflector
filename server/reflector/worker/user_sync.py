"""
Celery task for syncing users from Authentik API.

Periodically fetches all users from Authentik and synchronizes them
to the local user table. This ensures the user table stays up to date
with Authentik's user database.
"""

from typing import TypedDict

import structlog
from celery import shared_task

from reflector.asynctask import asynctask
from reflector.authentik_client import authentik_client
from reflector.db import get_database
from reflector.db.users import user_controller
from reflector.settings import settings

logger = structlog.get_logger(__name__)


class AuthentikUser(TypedDict):
    """Authentik user data structure."""

    uuid: str
    uid: str
    email: str | None


class SyncStats(TypedDict):
    """Statistics for user sync operation."""

    created: int
    updated: int
    skipped: int
    errors: int


async def sync_users_to_database(authentik_users: list[AuthentikUser]) -> SyncStats:
    """Sync Authentik users to the local database."""
    stats: SyncStats = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "errors": 0,
    }

    for authentik_user in authentik_users:
        user_id = authentik_user["uuid"]
        uid = authentik_user["uid"]
        email = authentik_user.get("email")

        if not email:
            logger.warning(f"User with uuid {user_id} has no email, skipping")
            stats["skipped"] += 1
            continue

        try:
            existing_user = await user_controller.get_by_uid(uid)
            await user_controller.create_or_update(id=user_id, uid=uid, email=email)

            if existing_user:
                if existing_user.email != email:
                    logger.info(
                        f"Updated user {email}: email changed from {existing_user.email}"
                    )
                    stats["updated"] += 1
                else:
                    logger.debug(f"User {email} unchanged")
                    stats["skipped"] += 1
            else:
                logger.info(f"Created user {email}")
                stats["created"] += 1

        except Exception as e:
            logger.error(f"Failed to sync user {email or uid}: {e}")
            stats["errors"] += 1

    return stats


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 300},
)
@asynctask
async def sync_users_from_authentik() -> SyncStats | None:
    """
    Celery task to sync users from Authentik to local database.

    Returns:
        SyncStats with counts of created/updated/skipped/errors,
        or None if Authentik is not configured.
    """
    if not settings.AUTHENTIK_API_URL or not settings.AUTHENTIK_API_TOKEN:
        logger.warning(
            "Authentik user sync skipped - AUTHENTIK_API_URL or "
            "AUTHENTIK_API_TOKEN not configured"
        )
        return None

    logger.info("Starting Authentik user sync")

    try:
        database = get_database()
        await database.connect()

        authentik_users = await authentik_client.get_all_users()

        if not authentik_users:
            logger.warning("No users fetched from Authentik")
            return None

        stats = await sync_users_to_database(authentik_users)

        logger.info(
            "Authentik user sync completed",
            created=stats["created"],
            updated=stats["updated"],
            skipped=stats["skipped"],
            errors=stats["errors"],
            total_fetched=len(authentik_users),
        )

        if stats["errors"] > 0:
            logger.warning(
                f"User sync completed with {stats['errors']} errors",
                stats=stats,
            )

        return stats

    finally:
        await database.disconnect()
