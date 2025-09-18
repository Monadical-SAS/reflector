from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from reflector.db.base import Base as Base
from reflector.db.base import metadata as metadata
from reflector.events import subscribers_shutdown, subscribers_startup
from reflector.settings import settings

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


import reflector.db.calendar_events  # noqa
import reflector.db.meetings  # noqa
import reflector.db.recordings  # noqa
import reflector.db.rooms  # noqa
import reflector.db.transcripts  # noqa


@subscribers_startup.append
async def database_connect(_):
    get_engine()


@subscribers_shutdown.append
async def database_disconnect(_):
    global _engine
    if _engine:
        await _engine.dispose()
        _engine = None
