"""Database utility functions."""

from reflector.db import database


def is_postgresql() -> bool:
    return database.url.scheme and database.url.scheme.startswith('postgresql')