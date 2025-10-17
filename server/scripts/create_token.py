"""Create API token for a user.

Usage:
    python create_token.py <user_id> <token_name>

Example:
    python create_token.py "user_oauth_sub_from_jwt" "Production Token"
"""

import asyncio
import sys

from reflector.db import get_database
from reflector.db.user_tokens import user_tokens_controller


async def create_token_for_user(user_id: str, name: str):
    """Create API token for a user"""
    await get_database().connect()

    try:
        token_model, plaintext = await user_tokens_controller.create_token(
            user_id=user_id,
            name=name,
        )
        print("✓ Token created successfully")
        print(f"  User ID: {user_id}")
        print(f"  Name: {name}")
        print(f"  Token ID: {token_model.id}")
        print(f"  Created: {token_model.created_at}")
        print()
        print("  API Token (save this, shown only once):")
        print(f"  {plaintext}")
        print()
        print("  Usage:")
        print(
            f"  curl -H 'X-API-Key: {plaintext}' http://localhost:1250/v1/transcripts"
        )
    finally:
        await get_database().disconnect()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python create_token.py <user_id> <token_name>")
        sys.exit(1)

    user_id = sys.argv[1]
    name = sys.argv[2]

    asyncio.run(create_token_for_user(user_id, name))
