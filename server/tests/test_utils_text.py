import pytest

from reflector.utils.text import clean_title


@pytest.mark.parametrize(
    "input_title,expected",
    [
        ("hello world", "Hello World"),
        ("HELLO WORLD", "Hello World"),
        ("hello WORLD", "Hello World"),
        ("the quick brown fox", "The Quick Brown fox"),
        ("discussion about API design", "Discussion About api Design"),
        ("Q1 2024 budget review", "Q1 2024 Budget Review"),
        ("'Title with quotes'", "Title With Quotes"),
        ("'title with quotes'", "Title With Quotes"),
        ("MiXeD CaSe WoRdS", "Mixed Case Words"),
    ],
)
def test_clean_title(input_title, expected):
    assert clean_title(input_title) == expected
