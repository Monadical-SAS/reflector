"""Provision admin user on server startup using environment variables.

Reads ADMIN_EMAIL and ADMIN_PASSWORD_HASH from settings and creates or updates
the admin user. Intended to be called from runserver.sh on container startup.
"""

import asyncio

from reflector.db.users import user_controller
from reflector.settings import settings
from reflector.utils import generate_uuid4


async def provision() -> None:
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD_HASH:
        return

    from reflector.db import get_database

    database = get_database()
    await database.connect()

    try:
        existing = await user_controller.get_by_email(settings.ADMIN_EMAIL)
        if existing:
            await user_controller.set_password_hash(
                existing.id, settings.ADMIN_PASSWORD_HASH
            )
            print(f"Updated admin user: {settings.ADMIN_EMAIL}")
        else:
            await user_controller.create_or_update(
                id=generate_uuid4(),
                authentik_uid=f"local:{settings.ADMIN_EMAIL}",
                email=settings.ADMIN_EMAIL,
                password_hash=settings.ADMIN_PASSWORD_HASH,
            )
            print(f"Created admin user: {settings.ADMIN_EMAIL}")
    finally:
        await database.disconnect()


if __name__ == "__main__":
    asyncio.run(provision())
