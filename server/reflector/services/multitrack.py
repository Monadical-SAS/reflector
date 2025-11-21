"""Service layer for multitrack audio processing.

This module provides business logic for processing multiple audio tracks
without any CLI-specific concerns. It can be used by CLI, API, or any
other interface.
"""

import asyncio
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol

import structlog
from celery.result import AsyncResult

from reflector.db import get_database
from reflector.db.transcripts import SourceKind, Transcript, transcripts_controller
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)

logger = structlog.get_logger(__name__)

# Maximum time to wait for multitrack processing (1 hour)
DEFAULT_PROCESSING_TIMEOUT_SECONDS = 3600

# Maximum error message length before truncation (database column constraint)
MAX_ERROR_MESSAGE_LENGTH = 500

# Interval between Celery task status checks
TASK_POLL_INTERVAL_SECONDS = 2


class StatusCallback(Protocol):
    """Callback for reporting multitrack task status updates."""

    def __call__(self, state: str, elapsed_seconds: int) -> None: ...


@dataclass
class MultitrackTaskResult:
    """Result from multitrack processing task."""

    success: bool
    transcript_id: str
    error: Optional[str] = None


async def create_multitrack_transcript(
    bucket_name: str,
    track_keys: List[str],
    source_language: str,
    target_language: str,
    user_id: Optional[str] = None,
) -> Transcript:
    """Create transcript entity for multitrack processing.

    Args:
        bucket_name: S3 bucket containing tracks
        track_keys: List of S3 keys for audio tracks
        source_language: Source language code
        target_language: Target language code
        user_id: Optional user ID

    Returns:
        Created transcript entity
    """
    num_tracks = len(track_keys)
    track_word = "track" if num_tracks == 1 else "tracks"
    transcript_name = f"Multitrack ({num_tracks} {track_word})"

    transcript = await transcripts_controller.add(
        transcript_name,
        source_kind=SourceKind.FILE,
        source_language=source_language,
        target_language=target_language,
        user_id=user_id,
    )

    logger.info(
        "Created multitrack transcript",
        transcript_id=transcript.id,
        name=transcript_name,
        bucket=bucket_name,
        num_tracks=len(track_keys),
    )

    return transcript


def submit_multitrack_task(
    transcript_id: str, bucket_name: str, track_keys: List[str]
) -> AsyncResult:
    """Submit multitrack processing task to Celery.

    Args:
        transcript_id: ID of transcript to process
        bucket_name: S3 bucket containing tracks
        track_keys: List of S3 keys for audio tracks

    Returns:
        Celery AsyncResult for tracking
    """
    result = task_pipeline_multitrack_process.delay(
        transcript_id=transcript_id,
        bucket_name=bucket_name,
        track_keys=track_keys,
    )

    logger.info(
        "Multitrack task submitted",
        transcript_id=transcript_id,
        task_id=result.id,
        bucket=bucket_name,
        num_tracks=len(track_keys),
    )

    return result


async def wait_for_task(
    result: AsyncResult,
    transcript_id: str,
    timeout_seconds: int = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    poll_interval: int = TASK_POLL_INTERVAL_SECONDS,
    status_callback: Optional[StatusCallback] = None,
) -> MultitrackTaskResult:
    """Wait for Celery task completion.

    Args:
        result: Celery AsyncResult to wait for
        transcript_id: ID of transcript being processed
        timeout_seconds: Maximum time to wait
        poll_interval: Seconds between status checks
        status_callback: Optional callback for status updates

    Returns:
        Task result with success status and any errors

    Raises:
        TimeoutError: If task doesn't complete within timeout
    """
    start_time = time.time()
    last_status = None

    while not result.ready():
        elapsed = time.time() - start_time
        if elapsed > timeout_seconds:
            error_msg = (
                f"Task {result.id} did not complete within {timeout_seconds}s "
                f"for transcript {transcript_id}"
            )
            logger.error(
                "Task timeout",
                task_id=result.id,
                transcript_id=transcript_id,
                elapsed_seconds=elapsed,
            )
            raise TimeoutError(error_msg)

        if result.state != last_status:
            if status_callback:
                status_callback(result.state, int(elapsed))
            last_status = result.state

        await asyncio.sleep(poll_interval)

    if result.failed():
        error_info = result.info
        traceback_info = getattr(result, "traceback", None)

        logger.error(
            "Multitrack task failed",
            transcript_id=transcript_id,
            task_id=result.id,
            error=str(error_info),
            has_traceback=bool(traceback_info),
        )

        error_detail = str(error_info)
        if traceback_info:
            error_detail += f"\nTraceback:\n{traceback_info}"

        return MultitrackTaskResult(
            success=False, transcript_id=transcript_id, error=error_detail
        )

    logger.info(
        "Multitrack task completed",
        transcript_id=transcript_id,
        task_id=result.id,
        state=result.state,
    )

    return MultitrackTaskResult(success=True, transcript_id=transcript_id)


async def update_transcript_status(
    transcript_id: str,
    status: str,
    error: Optional[str] = None,
    max_error_length: int = MAX_ERROR_MESSAGE_LENGTH,
) -> None:
    """Update transcript status in database.

    Args:
        transcript_id: ID of transcript to update
        status: New status value
        error: Optional error message
        max_error_length: Maximum length for error messages
    """
    database = get_database()
    connected = False

    try:
        await database.connect()
        connected = True

        transcript = await transcripts_controller.get_by_id(transcript_id)
        if transcript:
            update_data: Dict[str, Any] = {"status": status}

            if error:
                if len(error) > max_error_length:
                    error = error[: max_error_length - 3] + "..."
                update_data["error"] = error

            await transcripts_controller.update(transcript, update_data)

            logger.info(
                "Updated transcript status",
                transcript_id=transcript_id,
                status=status,
                has_error=bool(error),
            )
    except Exception as e:
        logger.warning(
            "Failed to update transcript status",
            transcript_id=transcript_id,
            error=str(e),
        )
    finally:
        if connected:
            try:
                await database.disconnect()
            except Exception as e:
                logger.warning(f"Database disconnect failed: {e}")


async def process_multitrack(
    bucket_name: str,
    track_keys: List[str],
    source_language: str,
    target_language: str,
    user_id: Optional[str] = None,
    timeout_seconds: int = DEFAULT_PROCESSING_TIMEOUT_SECONDS,
    status_callback: Optional[StatusCallback] = None,
) -> MultitrackTaskResult:
    """High-level orchestration for multitrack processing.

    Args:
        bucket_name: S3 bucket containing tracks
        track_keys: List of S3 keys for audio tracks
        source_language: Source language code
        target_language: Target language code
        user_id: Optional user ID
        timeout_seconds: Maximum processing time
        status_callback: Optional callback for status updates

    Returns:
        Processing result with transcript ID
    """
    database = get_database()
    transcript = None
    connected = False

    try:
        await database.connect()
        connected = True

        transcript = await create_multitrack_transcript(
            bucket_name=bucket_name,
            track_keys=track_keys,
            source_language=source_language,
            target_language=target_language,
            user_id=user_id,
        )

        result = submit_multitrack_task(
            transcript_id=transcript.id, bucket_name=bucket_name, track_keys=track_keys
        )

    except Exception as e:
        if transcript:
            try:
                await update_transcript_status(
                    transcript_id=transcript.id, status="failed", error=str(e)
                )
            except Exception as update_error:
                logger.error(
                    "Failed to update transcript status after error",
                    original_error=str(e),
                    update_error=str(update_error),
                    transcript_id=transcript.id,
                )
        raise
    finally:
        if connected:
            try:
                await database.disconnect()
            except Exception as e:
                logger.warning(f"Database disconnect failed: {e}")

    # Poll outside database connection
    task_result = await wait_for_task(
        result=result,
        transcript_id=transcript.id,
        timeout_seconds=timeout_seconds,
        poll_interval=2,
        status_callback=status_callback,
    )

    if not task_result.success:
        await update_transcript_status(
            transcript_id=transcript.id, status="failed", error=task_result.error
        )

    return task_result
