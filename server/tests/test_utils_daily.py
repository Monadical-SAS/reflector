import pytest

from reflector.utils.daily import extract_base_room_name


@pytest.mark.parametrize(
    "daily_room_name,expected",
    [
        ("daily-20251020193458", "daily"),
        ("daily-2-20251020193458", "daily-2"),
        ("my-room-name-20251020193458", "my-room-name"),
        ("room-with-numbers-123-20251020193458", "room-with-numbers-123"),
        ("x-20251020193458", "x"),
    ],
)
def test_extract_base_room_name(daily_room_name, expected):
    assert extract_base_room_name(daily_room_name) == expected
