import databases
import sqlalchemy
from reflector.events import subscribers_startup, subscribers_shutdown
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
    sqlalchemy.Column("summary", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("topics", sqlalchemy.JSON),
    sqlalchemy.Column("events", sqlalchemy.JSON),
    # with user attached, optional
    sqlalchemy.Column("user_id", sqlalchemy.String),
)

engine = sqlalchemy.create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)
metadata.create_all(engine)


async def database_connect():
    await database.connect()


async def database_disconnect():
    await database.disconnect()


subscribers_startup.append(database_connect)
subscribers_shutdown.append(database_disconnect)
