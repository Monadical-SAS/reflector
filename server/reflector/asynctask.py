import asyncio
import functools
from uuid import uuid4

from celery import current_task

from reflector.db import get_database
from reflector.llm import llm_session_id


def asynctask(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        async def run_with_db():
            task_id = current_task.request.id if current_task else None
            llm_session_id.set(task_id or f"random-{uuid4().hex}")
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
