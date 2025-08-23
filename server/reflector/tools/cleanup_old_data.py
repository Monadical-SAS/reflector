#!/usr/bin/env python
"""
Manual cleanup tool for old public data.
"""

import argparse
import asyncio
import sys
from datetime import datetime, timedelta, timezone

import structlog

from reflector.db import get_database
from reflector.db.meetings import meeting_consent, meetings
from reflector.db.recordings import recordings
from reflector.db.transcripts import transcripts, transcripts_controller
from reflector.settings import settings

logger = structlog.get_logger(__name__)


async def cleanup_old_data(days: int = 7, dry_run: bool = False):
    """
    Clean up old transcripts and meetings.

    Args:
        days: Number of days to keep data (default: 7)
        dry_run: If True, only show what would be deleted without actually deleting
    """
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    logger.info(
        "Starting cleanup",
        cutoff_date=cutoff_date.isoformat(),
        dry_run=dry_run,
        public_mode=settings.PUBLIC_MODE,
    )

    if not settings.PUBLIC_MODE:
        logger.warning(
            "WARNING: PUBLIC_MODE is False. "
            "This tool is intended for public instances. "
            "Proceeding anyway - be careful!"
        )

    query = transcripts.select().where(
        (transcripts.c.created_at < cutoff_date) & (transcripts.c.user_id.is_(None))
    )
    old_transcripts = await get_database().fetch_all(query)

    logger.info(f"Found {len(old_transcripts)} old anonymous transcripts")

    if dry_run:
        for t in old_transcripts[:10]:
            logger.info(
                "Would delete transcript",
                id=t["id"],
                name=t["name"],
                created_at=t["created_at"].isoformat(),
            )
        if len(old_transcripts) > 10:
            logger.info(f"... and {len(old_transcripts) - 10} more transcripts")
    else:
        deleted_count = 0
        for transcript_data in old_transcripts:
            try:
                await transcripts_controller.remove_by_id(transcript_data["id"])
                deleted_count += 1
                logger.info(
                    "Deleted transcript",
                    id=transcript_data["id"],
                    name=transcript_data["name"],
                )
            except Exception as e:
                logger.error(
                    "Failed to delete transcript",
                    id=transcript_data["id"],
                    error=str(e),
                )
        logger.info(f"Deleted {deleted_count} transcripts")

    query = meetings.select().where(
        (meetings.c.start_date < cutoff_date) & (meetings.c.user_id.is_(None))
    )
    old_meetings = await get_database().fetch_all(query)

    logger.info(f"Found {len(old_meetings)} old anonymous meetings")

    if dry_run:
        for m in old_meetings[:10]:
            logger.info(
                "Would delete meeting",
                id=m["id"],
                room_name=m["room_name"],
                start_date=m["start_date"].isoformat(),
            )
        if len(old_meetings) > 10:
            logger.info(f"... and {len(old_meetings) - 10} more meetings")
    else:
        deleted_count = 0
        for meeting_data in old_meetings:
            try:
                await get_database().execute(
                    meeting_consent.delete().where(
                        meeting_consent.c.meeting_id == meeting_data["id"]
                    )
                )
                await get_database().execute(
                    meetings.delete().where(meetings.c.id == meeting_data["id"])
                )
                deleted_count += 1
                logger.info(
                    "Deleted meeting",
                    id=meeting_data["id"],
                    room_name=meeting_data["room_name"],
                )
            except Exception as e:
                logger.error(
                    "Failed to delete meeting",
                    id=meeting_data["id"],
                    error=str(e),
                )
        logger.info(f"Deleted {deleted_count} meetings")

    query = transcripts.select().where(transcripts.c.recording_id.isnot(None))
    transcript_recordings = await get_database().fetch_all(query)
    referenced_recording_ids = {t["recording_id"] for t in transcript_recordings}

    query = recordings.select().where(recordings.c.recorded_at < cutoff_date)
    all_old_recordings = await get_database().fetch_all(query)

    orphaned_recordings = [
        r for r in all_old_recordings if r["id"] not in referenced_recording_ids
    ]

    logger.info(f"Found {len(orphaned_recordings)} orphaned recordings")

    if dry_run:
        for r in orphaned_recordings[:10]:
            logger.info(
                "Would delete recording",
                id=r["id"],
                object_key=r["object_key"],
                recorded_at=r["recorded_at"].isoformat(),
            )
        if len(orphaned_recordings) > 10:
            logger.info(f"... and {len(orphaned_recordings) - 10} more recordings")
    else:
        deleted_count = 0
        for recording_data in orphaned_recordings:
            try:
                await get_database().execute(
                    recordings.delete().where(recordings.c.id == recording_data["id"])
                )
                deleted_count += 1
                logger.info(
                    "Deleted recording",
                    id=recording_data["id"],
                    object_key=recording_data["object_key"],
                )
            except Exception as e:
                logger.error(
                    "Failed to delete recording",
                    id=recording_data["id"],
                    error=str(e),
                )
        logger.info(f"Deleted {deleted_count} recordings")

    logger.info("Cleanup completed")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old transcripts and meetings"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to keep data (default: 7)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be deleted without actually deleting",
    )

    args = parser.parse_args()

    if args.days < 1:
        logger.error("Days must be at least 1")
        sys.exit(1)

    asyncio.run(cleanup_old_data(days=args.days, dry_run=args.dry_run))


if __name__ == "__main__":
    main()
