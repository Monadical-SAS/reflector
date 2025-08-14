"""Database utility functions."""

from reflector.db import get_database


def is_postgresql() -> bool:
    return get_database().url.scheme and get_database().url.scheme.startswith(
        "postgresql"
    )
