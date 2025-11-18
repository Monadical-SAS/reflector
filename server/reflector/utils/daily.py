from reflector.utils.string import NonEmptyString

DailyRoomName = str


def recording_lock_key(recording_id: str) -> str:
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
