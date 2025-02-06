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
        yield lock
    finally:
        try:
            await lock.release()
        except Exception:
            pass


@asynccontextmanager
async def room_lock(room_id: str | None, ex: int = 10):
    room_id = room_id or "default"
    async with redis_lock(f"room:{room_id}") as lock:
        yield lock
