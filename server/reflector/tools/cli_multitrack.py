import asyncio
import sys
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
from reflector.storage import get_transcripts_storage
from reflector.tools.process import (
    extract_result_from_entry,
    parse_s3_url,
    validate_s3_objects,
)

logger = structlog.get_logger(__name__)

DEFAULT_PROCESSING_TIMEOUT_SECONDS = 3600

MAX_ERROR_MESSAGE_LENGTH = 500

TASK_POLL_INTERVAL_SECONDS = 2


class StatusCallback(Protocol):
    def __call__(self, state: str, elapsed_seconds: int) -> None: ...


@dataclass
class MultitrackTaskResult:
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
    """High-level orchestration for multitrack processing."""
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


def print_progress(message: str) -> None:
    """Print progress message to stderr for CLI visibility."""
    print(f"{message}", file=sys.stderr)


def create_status_callback() -> StatusCallback:
    """Create callback for task status updates during polling."""

    def callback(state: str, elapsed_seconds: int) -> None:
        print_progress(
            f"Multitrack pipeline status: {state} (elapsed: {elapsed_seconds}s)"
        )

    return callback


async def process_multitrack_cli(
    s3_urls: List[str],
    source_language: str,
    target_language: str,
    output_path: Optional[str] = None,
) -> None:
    if not s3_urls:
        raise ValueError("At least one track required for multitrack processing")

    bucket_keys = []
    for url in s3_urls:
        try:
            bucket, key = parse_s3_url(url)
            bucket_keys.append((bucket, key))
        except ValueError as e:
            raise ValueError(f"Invalid S3 URL '{url}': {e}") from e

    buckets = set(bucket for bucket, _ in bucket_keys)
    if len(buckets) > 1:
        raise ValueError(
            f"All tracks must be in the same S3 bucket. "
            f"Found {len(buckets)} different buckets: {sorted(buckets)}. "
            f"Please upload all files to a single bucket."
        )

    primary_bucket = bucket_keys[0][0]
    track_keys = [key for _, key in bucket_keys]

    print_progress(
        f"Starting multitrack CLI processing: "
        f"bucket={primary_bucket}, num_tracks={len(track_keys)}, "
        f"source_language={source_language}, target_language={target_language}"
    )

    storage = get_transcripts_storage()
    await validate_s3_objects(storage, bucket_keys)
    print_progress(f"S3 validation complete: {len(bucket_keys)} objects verified")

    result = await process_multitrack(
        bucket_name=primary_bucket,
        track_keys=track_keys,
        source_language=source_language,
        target_language=target_language,
        user_id=None,
        timeout_seconds=3600,
        status_callback=create_status_callback(),
    )

    if not result.success:
        error_msg = (
            f"Multitrack pipeline failed for transcript {result.transcript_id}\n"
        )
        if result.error:
            error_msg += f"Error: {result.error}\n"
        raise RuntimeError(error_msg)

    print_progress(
        f"Multitrack processing complete for transcript {result.transcript_id}"
    )

    database = get_database()
    await database.connect()
    try:
        await extract_result_from_entry(result.transcript_id, output_path)
    finally:
        await database.disconnect()
