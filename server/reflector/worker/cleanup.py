"""
Clean up old transcripts and meetings from public instances.
Deletes data older than PUBLIC_DATA_RETENTION_DAYS for anonymous users.
Will retry up to 3 times with 5-minute intervals on failure.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import TypedDict

import structlog
from celery import shared_task

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


async def cleanup_old_transcripts(cutoff_date: datetime, stats: CleanupStats):
    """Delete old anonymous transcripts."""
    query = transcripts.select().where(
        (transcripts.c.created_at < cutoff_date) & (transcripts.c.user_id.is_(None))
    )
    old_transcripts = await get_database().fetch_all(query)

    logger.info(f"Found {len(old_transcripts)} old transcripts to delete")

    for transcript_data in old_transcripts:
        transcript_id = transcript_data["id"]
        try:
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


async def cleanup_old_meetings(cutoff_date: datetime, stats: CleanupStats):
    """Delete old anonymous meetings and their consents."""
    query = meetings.select().where(
        (meetings.c.start_date < cutoff_date) & (meetings.c.user_id.is_(None))
    )
    old_meetings = await get_database().fetch_all(query)

    logger.info(f"Found {len(old_meetings)} old meetings to delete")

    for meeting_data in old_meetings:
        meeting_id = meeting_data["id"]
        try:
            await get_database().execute(
                meetings.delete().where(meetings.c.id == meeting_id)
            )
            stats["meetings_deleted"] += 1
            logger.info(
                "Deleted meeting",
                meeting_id=meeting_id,
                start_date=meeting_data["start_date"].isoformat(),
            )
        except Exception as e:
            error_msg = f"Failed to delete meeting {meeting_id}: {str(e)}"
            logger.error(error_msg, exc_info=e)
            stats["errors"].append(error_msg)


async def cleanup_orphaned_recordings(cutoff_date: datetime, stats: CleanupStats):
    """Delete orphaned recordings that are not referenced by any transcript."""
    query = transcripts.select().where(transcripts.c.recording_id.isnot(None))
    transcript_recordings = await get_database().fetch_all(query)
    referenced_recording_ids = {t["recording_id"] for t in transcript_recordings}

    query = recordings.select().where(recordings.c.recorded_at < cutoff_date)
    all_old_recordings = await get_database().fetch_all(query)

    orphaned_recordings = [
        r for r in all_old_recordings if r["id"] not in referenced_recording_ids
    ]

    logger.info(f"Found {len(orphaned_recordings)} orphaned recordings to delete")

    for recording_data in orphaned_recordings:
        recording_id = recording_data["id"]
        try:
            # Delete from storage first
            try:
                await get_recordings_storage().delete_file(recording_data["object_key"])
            except Exception as storage_error:
                logger.warning(
                    "Failed to delete recording from storage",
                    recording_id=recording_id,
                    object_key=recording_data["object_key"],
                    error=str(storage_error),
                )

            await get_database().execute(
                recordings.delete().where(recordings.c.id == recording_id)
            )
            stats["recordings_deleted"] += 1
            logger.info(
                "Deleted orphaned recording",
                recording_id=recording_id,
                recorded_at=recording_data["recorded_at"].isoformat(),
            )
        except Exception as e:
            error_msg = f"Failed to delete recording {recording_id}: {str(e)}"
            logger.error(error_msg, exc_info=e)
            stats["errors"].append(error_msg)


def log_cleanup_results(stats: CleanupStats):
    """Log the final cleanup results."""
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


async def _cleanup_old_public_data(days: int | None = None) -> CleanupStats | None:
    """
    Main cleanup logic for old public data.
    
    Args:
        days: Number of days to keep data. If None, uses PUBLIC_DATA_RETENTION_DAYS setting.
    
    Returns:
        CleanupStats or None if skipped
    """
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

    try:
        await cleanup_old_transcripts(cutoff_date, stats)
        await cleanup_old_meetings(cutoff_date, stats)
        await cleanup_orphaned_recordings(cutoff_date, stats)
    except Exception as e:
        logger.error("Cleanup task failed", exc_info=e)
        stats["errors"].append(f"Fatal error: {str(e)}")

    log_cleanup_results(stats)
    return stats


@shared_task(
    autoretry_for=(Exception,),
    retry_kwargs={"max_retries": 3, "countdown": 300},
)
@asynctask
def cleanup_old_public_data(days: int | None = None):
    """
    Celery task to clean up old public data.

    Args:
        days: Number of days to keep data. If None, uses PUBLIC_DATA_RETENTION_DAYS setting.
    """
    asyncio.run(_cleanup_old_public_data(days=days))
