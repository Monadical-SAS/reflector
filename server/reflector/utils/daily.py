import os
import re
from typing import NamedTuple

from reflector.utils.string import NonEmptyString

DailyRoomName = NonEmptyString


class DailyRecordingFilename(NamedTuple):
    """Parsed components from Daily.co recording filename.

    Format: {recording_start_ts}-{participant_id}-cam-audio-{track_start_ts}
    Example: 1763152299562-12f0b87c-97d4-4dd3-a65c-cee1f854a79c-cam-audio-1763152314582

    Note: S3 object keys have no extension, but browsers add .webm when downloading
    from S3 UI due to MIME type headers. If you download manually and wonder.
    """

    recording_start_ts: int
    participant_id: str
    track_start_ts: int


def parse_daily_recording_filename(filename: str) -> DailyRecordingFilename:
    """Parse Daily.co recording filename to extract timestamps and participant ID.

    Args:
        filename: Full path or basename of Daily.co recording file
                 Format: {recording_start_ts}-{participant_id}-cam-audio-{track_start_ts}

    Returns:
        DailyRecordingFilename with parsed components

    Raises:
        ValueError: If filename doesn't match expected format

    Examples:
        >>> parse_daily_recording_filename("1763152299562-12f0b87c-97d4-4dd3-a65c-cee1f854a79c-cam-audio-1763152314582")
        DailyRecordingFilename(recording_start_ts=1763152299562, participant_id='12f0b87c-97d4-4dd3-a65c-cee1f854a79c', track_start_ts=1763152314582)
    """
    base = os.path.basename(filename)
    pattern = r"(\d{13,})-([0-9a-fA-F-]{36})-cam-audio-(\d{13,})"
    match = re.search(pattern, base)

    if not match:
        raise ValueError(
            f"Invalid Daily.co recording filename: {filename}. "
            f"Expected format: {{recording_start_ts}}-{{participant_id}}-cam-audio-{{track_start_ts}}"
        )

    recording_start_ts = int(match.group(1))
    participant_id = match.group(2)
    track_start_ts = int(match.group(3))

    return DailyRecordingFilename(
        recording_start_ts=recording_start_ts,
        participant_id=participant_id,
        track_start_ts=track_start_ts,
    )


def recording_lock_key(recording_id: NonEmptyString) -> NonEmptyString:
    return f"recording:{recording_id}"


def extract_base_room_name(daily_room_name: DailyRoomName) -> NonEmptyString:
    """
    Extract base room name from Daily.co timestamped room name.

    Daily.co creates rooms with timestamp suffix: {base_name}-YYYYMMDDHHMMSS
    This function removes the timestamp to get the original room name.

    Examples:
        "daily-20251020193458" → "daily"
        "daily-2-20251020193458" → "daily-2"
        "my-room-name-20251020193458" → "my-room-name"

    Args:
        daily_room_name: Full Daily.co room name with optional timestamp

    Returns:
        Base room name without timestamp suffix
    """
    base_name = daily_room_name.rsplit("-", 1)[0]
    assert base_name, f"Extracted base name is empty from: {daily_room_name}"
    return base_name
