import databases
import sqlalchemy

from reflector.events import subscribers_shutdown, subscribers_startup
from reflector.settings import settings

database = databases.Database(settings.DATABASE_URL)
metadata = sqlalchemy.MetaData()


transcripts = sqlalchemy.Table(
    "transcript",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("locked", sqlalchemy.Boolean),
    sqlalchemy.Column("duration", sqlalchemy.Integer),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime),
    sqlalchemy.Column("title", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("short_summary", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("long_summary", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("topics", sqlalchemy.JSON),
    sqlalchemy.Column("events", sqlalchemy.JSON),
    sqlalchemy.Column("source_language", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("target_language", sqlalchemy.String, nullable=True),
    # with user attached, optional
    sqlalchemy.Column("user_id", sqlalchemy.String),
)

engine = sqlalchemy.create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)


@subscribers_startup.append
async def database_connect(_):
    await database.connect()


@subscribers_shutdown.append
async def database_disconnect(_):
    await database.disconnect()
