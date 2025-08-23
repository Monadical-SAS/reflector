import asyncio
from datetime import datetime, timedelta, timezone

import structlog
from celery import shared_task

from reflector.db import get_database
from reflector.db.meetings import meeting_consent, meetings
from reflector.db.recordings import recordings
from reflector.db.transcripts import transcripts, transcripts_controller
from reflector.settings import settings

logger = structlog.get_logger(__name__)


@shared_task(name="reflector.worker.cleanup.cleanup_old_public_data")
def cleanup_old_public_data():
    """
    Clean up old transcripts and meetings from public instances.
    Deletes data older than PUBLIC_DATA_RETENTION_DAYS for anonymous users.
    """
    asyncio.run(_cleanup_old_public_data())


async def _cleanup_old_public_data():
    """
    Actual cleanup logic for old public data.
    """
    if not settings.PUBLIC_MODE:
        logger.info("Skipping cleanup - not a public instance")
        return

    cutoff_date = datetime.now(timezone.utc) - timedelta(
        days=settings.PUBLIC_DATA_RETENTION_DAYS
    )
    logger.info(
        "Starting cleanup of old public data",
        cutoff_date=cutoff_date.isoformat(),
    )

    stats = {
        "transcripts_deleted": 0,
        "meetings_deleted": 0,
        "recordings_deleted": 0,
        "errors": [],
    }

    try:
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

        query = meetings.select().where(
            (meetings.c.start_date < cutoff_date) & (meetings.c.user_id.is_(None))
        )
        old_meetings = await get_database().fetch_all(query)

        logger.info(f"Found {len(old_meetings)} old meetings to delete")

        for meeting_data in old_meetings:
            meeting_id = meeting_data["id"]
            try:
                await get_database().execute(
                    meeting_consent.delete().where(
                        meeting_consent.c.meeting_id == meeting_id
                    )
                )

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
                from reflector.storage import get_recordings_storage

                try:
                    await get_recordings_storage().delete_file(
                        recording_data["object_key"]
                    )
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

    except Exception as e:
        logger.error("Cleanup task failed", exc_info=e)
        stats["errors"].append(f"Fatal error: {str(e)}")

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

    return stats
