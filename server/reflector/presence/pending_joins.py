"""Track pending join intents in Redis.

When a user signals intent to join a meeting (before WebRTC handshake completes),
we store a pending join record. This prevents the meeting from being deactivated
while users are still connecting.
"""

import time

from redis.asyncio import Redis

from reflector.logger import logger

PENDING_JOIN_TTL = 30  # seconds
PENDING_JOIN_PREFIX = "pending_join"
# Max keys to scan per Redis SCAN iteration
SCAN_BATCH_SIZE = 100


async def create_pending_join(redis: Redis, meeting_id: str, user_id: str) -> None:
    """Create a pending join record. Called before WebRTC handshake."""
    key = f"{PENDING_JOIN_PREFIX}:{meeting_id}:{user_id}"
    log = logger.bind(meeting_id=meeting_id, user_id=user_id, key=key)
    await redis.setex(key, PENDING_JOIN_TTL, str(time.time()))
    log.debug("Created pending join")


async def delete_pending_join(redis: Redis, meeting_id: str, user_id: str) -> None:
    """Delete pending join. Called after WebRTC connection established."""
    key = f"{PENDING_JOIN_PREFIX}:{meeting_id}:{user_id}"
    log = logger.bind(meeting_id=meeting_id, user_id=user_id, key=key)
    await redis.delete(key)
    log.debug("Deleted pending join")


async def has_pending_joins(redis: Redis, meeting_id: str) -> bool:
    """Check if meeting has any pending joins.

    Uses Redis SCAN to iterate through all keys matching the pattern.
    Properly iterates until cursor returns 0 to ensure all keys are checked.
    """
    pattern = f"{PENDING_JOIN_PREFIX}:{meeting_id}:*"
    log = logger.bind(meeting_id=meeting_id, pattern=pattern)

    cursor = 0
    iterations = 0
    while True:
        cursor, keys = await redis.scan(
            cursor=cursor, match=pattern, count=SCAN_BATCH_SIZE
        )
        iterations += 1
        if keys:
            log.debug("Found pending joins", count=len(keys), iterations=iterations)
            return True
        if cursor == 0:
            break

    log.debug("No pending joins found", iterations=iterations)
    return False
