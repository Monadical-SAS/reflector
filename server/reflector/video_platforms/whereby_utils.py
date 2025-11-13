import re
from datetime import datetime

from reflector.utils.datetime import parse_datetime_with_timezone
from reflector.utils.string import NonEmptyString, parse_non_empty_string
from reflector.video_platforms.base import ROOM_PREFIX_SEPARATOR


def parse_whereby_recording_filename(
    object_key: NonEmptyString,
) -> (NonEmptyString, datetime):
    filename = parse_non_empty_string(object_key.rsplit(".", 1)[0])
    timestamp_pattern = r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)"
    match = re.search(timestamp_pattern, filename)
    if not match:
        raise ValueError(f"No ISO timestamp found in filename: {object_key}")
    timestamp_str = match.group(1)
    timestamp_start = match.start(1)
    room_name_part = filename[:timestamp_start]
    if room_name_part.endswith(ROOM_PREFIX_SEPARATOR):
        room_name_part = room_name_part[: -len(ROOM_PREFIX_SEPARATOR)]
    else:
        raise ValueError(
            f"room name {room_name_part} doesnt have {ROOM_PREFIX_SEPARATOR} at the end of filename: {object_key}"
        )

    return parse_non_empty_string(room_name_part), parse_datetime_with_timezone(
        timestamp_str
    )


def whereby_room_name_prefix(room_name_prefix: NonEmptyString) -> NonEmptyString:
    return room_name_prefix + ROOM_PREFIX_SEPARATOR


# room name comes with "/" from whereby api but lacks "/" e.g. in recording filenames
def room_name_to_whereby_api_room_name(room_name: NonEmptyString) -> NonEmptyString:
    return f"/{room_name}"
