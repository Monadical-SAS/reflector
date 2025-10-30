import re

DailyRoomName = str


def extract_base_room_name(daily_room_name: DailyRoomName) -> str:
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
    timestamp_match = re.search(r"-(\d{14})$", daily_room_name)
    if timestamp_match:
        return daily_room_name[: -len(timestamp_match.group(0))]
    else:
        raise ValueError(f"Invalid Daily.co room name {daily_room_name}")
