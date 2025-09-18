from datetime import datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from reflector.db.base import CalendarEventModel
from reflector.utils import generate_uuid4


class CalendarEvent(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    room_id: str
    ics_uid: str
    title: str | None = None
    description: str | None = None
    start_time: datetime
    end_time: datetime
    attendees: list[dict[str, Any]] | None = None
    location: str | None = None
    ics_raw_data: str | None = None
    last_synced: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_deleted: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CalendarEventController:
    async def get_upcoming_events(
        self,
        session: AsyncSession,
        room_id: str,
        current_time: datetime,
        buffer_minutes: int = 15,
    ) -> list[CalendarEvent]:
        buffer_time = current_time + timedelta(minutes=buffer_minutes)

        query = (
            select(CalendarEventModel)
            .where(
                sa.and_(
                    CalendarEventModel.room_id == room_id,
                    CalendarEventModel.start_time <= buffer_time,
                    CalendarEventModel.end_time > current_time,
                )
            )
            .order_by(CalendarEventModel.start_time)
        )

        result = await session.execute(query)
        return [CalendarEvent(**row.__dict__) for row in result.scalars().all()]

    async def get_by_id(
        self, session: AsyncSession, event_id: str
    ) -> CalendarEvent | None:
        query = select(CalendarEventModel).where(CalendarEventModel.id == event_id)
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return CalendarEvent(**row.__dict__)

    async def get_by_ics_uid(
        self, session: AsyncSession, room_id: str, ics_uid: str
    ) -> CalendarEvent | None:
        query = select(CalendarEventModel).where(
            sa.and_(
                CalendarEventModel.room_id == room_id,
                CalendarEventModel.ics_uid == ics_uid,
            )
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return CalendarEvent(**row.__dict__)

    async def upsert(
        self, session: AsyncSession, event: CalendarEvent
    ) -> CalendarEvent:
        existing = await self.get_by_ics_uid(session, event.room_id, event.ics_uid)

        if existing:
            event.updated_at = datetime.now(timezone.utc)
            query = (
                update(CalendarEventModel)
                .where(CalendarEventModel.id == existing.id)
                .values(**event.model_dump(exclude={"id"}))
            )
            await session.execute(query)
            await session.commit()
            return event
        else:
            new_event = CalendarEventModel(**event.model_dump())
            session.add(new_event)
            await session.commit()
            return event

    async def delete_old_events(
        self, session: AsyncSession, room_id: str, cutoff_date: datetime
    ) -> int:
        query = delete(CalendarEventModel).where(
            sa.and_(
                CalendarEventModel.room_id == room_id,
                CalendarEventModel.end_time < cutoff_date,
            )
        )
        result = await session.execute(query)
        await session.commit()
        return result.rowcount

    async def delete_events_not_in_list(
        self, session: AsyncSession, room_id: str, keep_ics_uids: list[str]
    ) -> int:
        if not keep_ics_uids:
            query = delete(CalendarEventModel).where(
                CalendarEventModel.room_id == room_id
            )
        else:
            query = delete(CalendarEventModel).where(
                sa.and_(
                    CalendarEventModel.room_id == room_id,
                    CalendarEventModel.ics_uid.notin_(keep_ics_uids),
                )
            )

        result = await session.execute(query)
        await session.commit()
        return result.rowcount

    async def get_by_room(
        self, session: AsyncSession, room_id: str, include_deleted: bool = True
    ) -> list[CalendarEvent]:
        query = select(CalendarEventModel).where(CalendarEventModel.room_id == room_id)
        if not include_deleted:
            query = query.where(CalendarEventModel.is_deleted == False)
        result = await session.execute(query)
        return [CalendarEvent(**row.__dict__) for row in result.scalars().all()]

    async def get_upcoming(
        self, session: AsyncSession, room_id: str, minutes_ahead: int = 120
    ) -> list[CalendarEvent]:
        now = datetime.now(timezone.utc)
        buffer_time = now + timedelta(minutes=minutes_ahead)

        query = (
            select(CalendarEventModel)
            .where(
                sa.and_(
                    CalendarEventModel.room_id == room_id,
                    CalendarEventModel.start_time <= buffer_time,
                    CalendarEventModel.end_time > now,
                    CalendarEventModel.is_deleted == False,
                )
            )
            .order_by(CalendarEventModel.start_time)
        )

        result = await session.execute(query)
        return [CalendarEvent(**row.__dict__) for row in result.scalars().all()]

    async def soft_delete_missing(
        self, session: AsyncSession, room_id: str, current_ics_uids: list[str]
    ) -> int:
        query = (
            update(CalendarEventModel)
            .where(
                sa.and_(
                    CalendarEventModel.room_id == room_id,
                    CalendarEventModel.ics_uid.notin_(current_ics_uids)
                    if current_ics_uids
                    else True,
                    CalendarEventModel.end_time > datetime.now(timezone.utc),
                )
            )
            .values(is_deleted=True)
        )
        result = await session.execute(query)
        await session.commit()
        return result.rowcount


calendar_events_controller = CalendarEventController()
