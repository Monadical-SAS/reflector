"""
Main task for cleanup old public data.

Deletes old anonymous transcripts and their associated meetings/recordings.
Transcripts are the main entry point - any associated data is also removed.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import structlog
from celery import shared_task
from databases import Database
from pydantic.types import PositiveInt

from reflector.asynctask import asynctask
from reflector.db import get_database
from reflector.db.meetings import meetings
from reflector.db.recordings import recordings
from reflector.db.transcripts import transcripts, transcripts_controller
from reflector.settings import settings
from reflector.storage import get_recordings_storage

logger = structlog.get_logger(__name__)


class CleanupStats(TypedDict):
    """Statistics for cleanup operation."""

    transcripts_deleted: int
    meetings_deleted: int
    recordings_deleted: int
    errors: list[str]


async def delete_single_transcript(
    db: Database, transcript_data: dict, stats: CleanupStats
):
    transcript_id = transcript_data["id"]
    meeting_id = transcript_data["meeting_id"]
    recording_id = transcript_data["recording_id"]

    try:
        async with db.transaction(isolation="serializable"):
            if meeting_id:
                await db.execute(meetings.delete().where(meetings.c.id == meeting_id))
                stats["meetings_deleted"] += 1
                logger.info("Deleted associated meeting", meeting_id=meeting_id)

            if recording_id:
                recording = await db.fetch_one(
                    recordings.select().where(recordings.c.id == recording_id)
                )
                if recording:
                    try:
                        await get_recordings_storage().delete_file(
                            recording["object_key"]
                        )
                    except Exception as storage_error:
                        logger.warning(
                            "Failed to delete recording from storage",
                            recording_id=recording_id,
                            object_key=recording["object_key"],
                            error=str(storage_error),
                        )

                    await db.execute(
                        recordings.delete().where(recordings.c.id == recording_id)
                    )
                    stats["recordings_deleted"] += 1
                    logger.info(
                        "Deleted associated recording", recording_id=recording_id
                    )

            await transcripts_controller.remove_by_id(transcript_id)
            stats["transcripts_deleted"] += 1
            logger.info(
                "Deleted transcript",
                transcript_id=transcript_id,
                created_at=transcript_data["created_at"].isoformat(),
            )
    except Exception as e:
        error_msg = f"Failed to delete transcript {transcript_id}: {str(e)}"
        logger.error(error_msg, exc_info=e)
        stats["errors"].append(error_msg)


async def cleanup_old_transcripts(
    db: Database, cutoff_date: datetime, stats: CleanupStats
):
    """Delete old anonymous transcripts and their associated recordings/meetings."""
    query = transcripts.select().where(
        (transcripts.c.created_at < cutoff_date) & (transcripts.c.user_id.is_(None))
    )
    old_transcripts = await db.fetch_all(query)

    logger.info(f"Found {len(old_transcripts)} old transcripts to delete")

    for transcript_data in old_transcripts:
        await delete_single_transcript(db, transcript_data, stats)


def log_cleanup_results(stats: CleanupStats):
    logger.info(
        "Cleanup completed",
        transcripts_deleted=stats["transcripts_deleted"],
        meetings_deleted=stats["meetings_deleted"],
        recordings_deleted=stats["recordings_deleted"],
        errors_count=len(stats["errors"]),
    )

    if stats["errors"]:
        logger.warning(
            "Cleanup completed with errors",
            errors=stats["errors"][:10],
        )


async def cleanup_old_public_data(
    days: PositiveInt | None = None,
) -> CleanupStats | None:
    if days is None:
        days = settings.PUBLIC_DATA_RETENTION_DAYS

    if not settings.PUBLIC_MODE:
        logger.info("Skipping cleanup - not a public instance")
        return None

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    logger.info(
        "Starting cleanup of old public data",
        cutoff_date=cutoff_date.isoformat(),
    )

    stats: CleanupStats = {
        "transcripts_deleted": 0,
        "meetings_deleted": 0,
        "recordings_deleted": 0,
        "errors": [],
    }

    db = get_database()
    await _cleanup_old_transcripts(db, cutoff_date, stats)

    log_cleanup_results(stats)
    return stats


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 300},
)
@asynctask
def cleanup_old_public_data_task(days: int | None = None):
    asyncio.run(cleanup_old_public_data(days=days))
