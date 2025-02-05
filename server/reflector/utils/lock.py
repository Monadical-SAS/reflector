from contextlib import asynccontextmanager

import redis.asyncio as redis
from reflector.settings import settings

client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    db=settings.REDIS_LOCK_DB,
)


@asynccontextmanager
async def redis_lock(key: str, ex: int = 10):
    lock = client.lock(f"lock:{key}", ex)
    try:
        await lock.acquire()
        yield client
    finally:
        try:
            await lock.release()
        except Exception:
            pass
