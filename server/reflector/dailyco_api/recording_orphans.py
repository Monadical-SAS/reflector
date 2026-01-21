"""Utility for creating orphan recordings."""

import os
from datetime import datetime, timezone

from reflector.db.recordings import Recording, recordings_controller
from reflector.logger import logger
from reflector.utils.string import NonEmptyString


async def create_and_log_orphan(
    recording_id: NonEmptyString,
    bucket_name: str,
    room_name: str,
    start_ts: int,
    track_keys: list[str] | None,
    source: str,
) -> bool:
    """Create orphan recording and log if first occurrence.

    Args:
        recording_id: Daily.co recording ID
        bucket_name: S3 bucket (empty string for cloud recordings)
        room_name: Daily.co room name
        start_ts: Unix timestamp
        track_keys: Track keys for raw-tracks, None for cloud
        source: "webhook" or "polling" for logging

    Returns:
        True if created (first poller), False if already exists
    """
    if track_keys:
        object_key = os.path.dirname(track_keys[0]) if track_keys else room_name
    else:
        object_key = room_name

    created = await recordings_controller.create_orphan(
        Recording(
            id=recording_id,
            bucket_name=bucket_name,
            object_key=object_key,
            recorded_at=datetime.fromtimestamp(start_ts, tz=timezone.utc),
            track_keys=track_keys,
            meeting_id=None,
            status="orphan",
        )
    )

    if created:
        logger.error(
            f"Orphan recording ({source})",
            recording_id=recording_id,
            room_name=room_name,
        )

    return created
