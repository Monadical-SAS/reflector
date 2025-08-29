import asyncio
import functools

from reflector.db import get_database


def asynctask(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        async def run_with_db():
            database = get_database()
            await database.connect()
            try:
                return await f(*args, **kwargs)
            finally:
                await database.disconnect()

        coro = run_with_db()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.run_until_complete(coro)
        return asyncio.run(coro)

    return wrapper
