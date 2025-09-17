import asyncio
import functools
import json
from typing import Optional

import redis
import redis.asyncio as redis_async
import structlog
from redis.exceptions import LockError

from reflector.settings import settings

logger = structlog.get_logger(__name__)

redis_clients = {}


def get_redis_client(db=0):
    """
    Get a Redis client for the specified database.
    """
    if db not in redis_clients:
        redis_clients[db] = redis.StrictRedis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=db,
        )
    return redis_clients[db]


async def get_async_redis_client(db: int = 0):
    return await redis_async.from_url(
        f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{db}"
    )


def redis_cache(prefix="cache", duration=3600, db=settings.REDIS_CACHE_DB, argidx=1):
    """
    Cache the result of a function in Redis.
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Check if the first argument is a string
            if len(args) < (argidx + 1) or not isinstance(args[argidx], str):
                return func(*args, **kwargs)

            # Compute the cache key based on the arguments and prefix
            cache_key = prefix + ":" + args[argidx]
            redis_client = get_redis_client(db=db)
            cached_result = redis_client.get(cache_key)

            if cached_result:
                return json.loads(cached_result.decode("utf-8"))

            # If the result is not cached, call the original function
            result = func(*args, **kwargs)
            redis_client.setex(cache_key, duration, json.dumps(result))
            return result

        return wrapper

    return decorator


class RedisAsyncLock:
    def __init__(
        self,
        key: str,
        timeout: int = 120,
        extend_interval: int = 30,
        skip_if_locked: bool = False,
        blocking: bool = True,
        blocking_timeout: Optional[float] = None,
    ):
        self.key = f"async_lock:{key}"
        self.timeout = timeout
        self.extend_interval = extend_interval
        self.skip_if_locked = skip_if_locked
        self.blocking = blocking
        self.blocking_timeout = blocking_timeout
        self._lock = None
        self._redis = None
        self._extend_task = None
        self._acquired = False

    async def _extend_lock_periodically(self):
        while True:
            try:
                await asyncio.sleep(self.extend_interval)
                if self._lock:
                    await self._lock.extend(self.timeout, replace_ttl=True)
                    logger.debug("Extended lock", key=self.key)
            except LockError:
                logger.warning("Failed to extend lock", key=self.key)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error("Error extending lock", key=self.key, error=str(e))
                break

    async def __aenter__(self):
        self._redis = await get_async_redis_client()
        self._lock = self._redis.lock(
            self.key,
            timeout=self.timeout,
            blocking=self.blocking,
            blocking_timeout=self.blocking_timeout,
        )

        self._acquired = await self._lock.acquire()

        if not self._acquired:
            if self.skip_if_locked:
                logger.warning(
                    "Lock already acquired by another process, skipping", key=self.key
                )
                return self
            else:
                raise LockError(f"Failed to acquire lock: {self.key}")

        self._extend_task = asyncio.create_task(self._extend_lock_periodically())
        logger.info("Acquired lock", key=self.key)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._extend_task:
            self._extend_task.cancel()
            try:
                await self._extend_task
            except asyncio.CancelledError:
                pass

        if self._acquired and self._lock:
            try:
                await self._lock.release()
                logger.info("Released lock", key=self.key)
            except LockError:
                logger.debug("Lock already released or expired", key=self.key)

        if self._redis:
            await self._redis.aclose()

    @property
    def acquired(self) -> bool:
        return self._acquired
