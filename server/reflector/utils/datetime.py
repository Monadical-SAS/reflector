from datetime import datetime, timezone


def parse_datetime_with_timezone(iso_string: str) -> datetime:
    """Parse ISO datetime string and ensure timezone awareness (defaults to UTC if naive)."""
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt
