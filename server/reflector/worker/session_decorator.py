"""
Session management decorator for async worker tasks.

This decorator ensures that all worker tasks have a properly managed database session
that stays open for the entire duration of the task execution.
"""

import functools
from typing import Any, Callable, TypeVar

from reflector.db import get_session_factory

F = TypeVar("F", bound=Callable[..., Any])


def with_session(func: F) -> F:
    """
    Decorator that provides an AsyncSession as the first argument to the decorated function.

    This should be used AFTER the @asynctask decorator on Celery tasks to ensure
    proper session management throughout the task execution.

    Example:
        @shared_task
        @asynctask
        @with_session
        async def my_task(session: AsyncSession, arg1: str, arg2: int):
            # session is automatically provided and managed
            result = await some_controller.get_by_id(session, arg1)
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                # Pass session as first argument to the decorated function
                return await func(session, *args, **kwargs)

    return wrapper
