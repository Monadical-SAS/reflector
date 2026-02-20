"""Create or update an admin user with password authentication.

Usage:
    uv run python -m reflector.tools.create_admin --email admin@localhost --password <pass>
    uv run python -m reflector.tools.create_admin --email admin@localhost  # prompts for password
    uv run python -m reflector.tools.create_admin --hash-only --password <pass>  # print hash only
"""

import argparse
import asyncio
import getpass
import sys

from reflector.auth.password_utils import hash_password
from reflector.db.users import user_controller
from reflector.utils import generate_uuid4


async def create_admin(email: str, password: str) -> None:
    from reflector.db import get_database

    database = get_database()
    await database.connect()

    try:
        password_hash = hash_password(password)

        existing = await user_controller.get_by_email(email)
        if existing:
            await user_controller.set_password_hash(existing.id, password_hash)
            print(f"Updated password for existing user: {email} (id={existing.id})")
        else:
            user = await user_controller.create_or_update(
                id=generate_uuid4(),
                authentik_uid=f"local:{email}",
                email=email,
                password_hash=password_hash,
            )
            print(f"Created admin user: {email} (id={user.id})")
    finally:
        await database.disconnect()


def main():
    parser = argparse.ArgumentParser(description="Create or update an admin user")
    parser.add_argument(
        "--email", default="admin@localhost", help="Admin email address"
    )
    parser.add_argument(
        "--password",
        help="Admin password (will prompt if not provided)",
    )
    parser.add_argument(
        "--hash-only",
        action="store_true",
        help="Print the password hash and exit (for ADMIN_PASSWORD_HASH env var)",
    )
    args = parser.parse_args()

    password = args.password
    if not password:
        password = getpass.getpass("Password: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("Passwords do not match", file=sys.stderr)
            sys.exit(1)

    if not password:
        print("Password cannot be empty", file=sys.stderr)
        sys.exit(1)

    if args.hash_only:
        print(hash_password(password))
        sys.exit(0)

    asyncio.run(create_admin(args.email, password))


if __name__ == "__main__":
    main()
