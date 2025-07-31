import databases
import sqlalchemy
from reflector.events import subscribers_shutdown, subscribers_startup
from reflector.settings import settings

database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()

# import models
import reflector.db.jobs  # noqa
import reflector.db.meetings  # noqa
import reflector.db.recordings  # noqa
import reflector.db.rooms  # noqa
import reflector.db.transcripts  # noqa

kwargs = {}
if "sqlite" in settings.DATABASE_URL:
    kwargs["connect_args"] = {"check_same_thread": False}
engine = sqlalchemy.create_engine(settings.DATABASE_URL, **kwargs)


@subscribers_startup.append
async def database_connect(_):
    await database.connect()


@subscribers_shutdown.append
async def database_disconnect(_):
    await database.disconnect()
