import contextvars
from typing import Optional

import databases
import sqlalchemy

from reflector.events import subscribers_shutdown, subscribers_startup
from reflector.settings import settings

metadata = sqlalchemy.MetaData()

_database_context: contextvars.ContextVar[Optional[databases.Database]] = (
    contextvars.ContextVar("database", default=None)
)


def get_database() -> databases.Database:
    """Get database instance for current asyncio context"""
    db = _database_context.get()
    if db is None:
        db = databases.Database(settings.DATABASE_URL)
        _database_context.set(db)
    return db


# import models
import reflector.db.calendar_events  # noqa
import reflector.db.daily_participant_sessions  # noqa
import reflector.db.daily_recording_requests  # noqa
import reflector.db.meetings  # noqa
import reflector.db.recordings  # noqa
import reflector.db.rooms  # noqa
import reflector.db.transcripts  # noqa
import reflector.db.user_api_keys  # noqa
import reflector.db.users  # noqa

kwargs = {}
if "postgres" not in settings.DATABASE_URL:
    raise Exception("Only postgres database is supported in reflector")
engine = sqlalchemy.create_engine(settings.DATABASE_URL, **kwargs)


@subscribers_startup.append
async def database_connect(_):
    database = get_database()
    await database.connect()


@subscribers_shutdown.append
async def database_disconnect(_):
    database = get_database()
    await database.disconnect()
