import asyncio
import functools
from uuid import uuid4

from celery import current_task

from reflector.db import _database_context, get_database
from reflector.llm import llm_session_id
from reflector.ws_manager import reset_ws_manager


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
                _database_context.set(None)

        if current_task:
            # Reset cached connections before each Celery task.
            # Each asyncio.run() creates a new event loop, making connections
            # from previous tasks stale ("Future attached to a different loop").
            _database_context.set(None)
            reset_ws_manager()

        coro = run_with_db()
        if current_task:
            return asyncio.run(coro)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.run_until_complete(coro)
        return asyncio.run(coro)

    return wrapper
