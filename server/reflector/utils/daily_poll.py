"""Simple Daily.co polling functions - no complex state machine needed."""

import structlog

from reflector.redis_cache import get_redis_client

logger = structlog.get_logger(__name__)


async def request_meeting_poll(meeting_id: str) -> None:
    """Request a poll for a meeting (set Redis flag)."""
    redis = await get_redis_client()
    await redis.set(f"meeting_poll_requested:{meeting_id}", "1")
    logger.info("Poll requested", meeting_id=meeting_id)


async def try_claim_meeting_poll(meeting_id: str) -> bool:
    """Try to atomically claim a poll flag. Returns True if claimed."""
    redis = await get_redis_client()
    flag_value = await redis.getdel(f"meeting_poll_requested:{meeting_id}")

    if flag_value:
        logger.debug("Poll flag claimed", meeting_id=meeting_id)
        return True
    return False
