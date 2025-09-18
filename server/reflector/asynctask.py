import asyncio
import functools


def asynctask(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        async def run_async():
            return await f(*args, **kwargs)

        coro = run_async()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.run_until_complete(coro)
        return asyncio.run(coro)

    return wrapper
