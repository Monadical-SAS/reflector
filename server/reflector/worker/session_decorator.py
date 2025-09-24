"""
Session management decorator for async worker tasks.

This decorator ensures that all worker tasks have a properly managed database session
that stays open for the entire duration of the task execution.
"""

import functools
from typing import Any, Callable, TypeVar

from celery import current_task

from reflector.db import get_session_factory
from reflector.db.transcripts import transcripts_controller
from reflector.logger import logger

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


def with_session_and_transcript(func: F) -> F:
    """
    Decorator that provides both an AsyncSession and a Transcript to the decorated function.

    This decorator:
    1. Extracts transcript_id from kwargs
    2. Creates and manages a database session
    3. Fetches the transcript using the session
    4. Creates an enhanced logger with Celery task context
    5. Passes session, transcript, and logger to the decorated function

    This should be used AFTER the @asynctask decorator on Celery tasks.

    Example:
        @shared_task
        @asynctask
        @with_session_and_transcript
        async def my_task(session: AsyncSession, transcript: Transcript, logger: Logger, arg1: str):
            # session, transcript, and logger are automatically provided
            room = await rooms_controller.get_by_id(session, transcript.room_id)
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        transcript_id = kwargs.pop("transcript_id", None)
        if not transcript_id:
            raise ValueError(
                "transcript_id is required for @with_session_and_transcript"
            )

        session_factory = get_session_factory()
        async with session_factory() as session:
            async with session.begin():
                # Fetch the transcript
                transcript = await transcripts_controller.get_by_id(
                    session, transcript_id
                )
                if not transcript:
                    raise Exception(f"Transcript {transcript_id} not found")

                # Create enhanced logger with Celery task context
                tlogger = logger.bind(transcript_id=transcript.id)
                if current_task:
                    tlogger = tlogger.bind(
                        task_id=current_task.request.id,
                        task_name=current_task.name,
                        worker_hostname=current_task.request.hostname,
                        task_retries=current_task.request.retries,
                        transcript_id=transcript_id,
                    )

                try:
                    # Pass session, transcript, and logger to the decorated function
                    return await func(
                        session, transcript=transcript, logger=tlogger, *args, **kwargs
                    )
                except Exception:
                    tlogger.exception("Error in task execution")
                    raise

    return wrapper
