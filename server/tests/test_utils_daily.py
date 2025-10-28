import pytest

from reflector.utils.daily import extract_base_room_name


@pytest.mark.parametrize(
    "daily_room_name,expected",
    [
        # Standard Daily.co timestamped rooms
        ("daily-20251020193458", "daily"),
        ("daily-2-20251020193458", "daily-2"),
        ("my-room-name-20251020193458", "my-room-name"),
        # Rooms without timestamps (should remain unchanged)
        ("no-timestamp-room", "no-timestamp-room"),
        ("simple", "simple"),
        # Edge cases
        ("room-with-numbers-123-20251020193458", "room-with-numbers-123"),
        ("x-20251020193458", "x"),  # Single char base name
        # Room without timestamp but similar pattern
        ("almost-timestamp-2025102", "almost-timestamp-2025102"),  # Only 13 digits
        (
            "almost-timestamp-202510201934589",
            "almost-timestamp-202510201934589",
        ),  # 15 digits
    ],
)
def test_extract_base_room_name(daily_room_name, expected):
    assert extract_base_room_name(daily_room_name) == expected
