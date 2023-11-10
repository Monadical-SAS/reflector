import functools
import json

import redis
from reflector.settings import settings

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
