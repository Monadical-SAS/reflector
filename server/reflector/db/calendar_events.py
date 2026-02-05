from datetime import datetime, timedelta, timezone
from typing import Any

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import JSONB

from reflector.db import get_database, metadata
from reflector.utils import generate_uuid4

calendar_events = sa.Table(
    "calendar_event",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column(
        "room_id",
        sa.String,
        sa.ForeignKey("room.id", ondelete="CASCADE", name="fk_calendar_event_room_id"),
        nullable=False,
    ),
    sa.Column("ics_uid", sa.Text, nullable=False),
    sa.Column("title", sa.Text),
    sa.Column("description", sa.Text),
    sa.Column("start_time", sa.DateTime(timezone=True), nullable=False),
    sa.Column("end_time", sa.DateTime(timezone=True), nullable=False),
    sa.Column("attendees", JSONB),
    sa.Column("location", sa.Text),
    sa.Column("ics_raw_data", sa.Text),
    sa.Column("last_synced", sa.DateTime(timezone=True), nullable=False),
    sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    sa.UniqueConstraint("room_id", "ics_uid", name="uq_room_calendar_event"),
    sa.Index("idx_calendar_event_room_start", "room_id", "start_time"),
    sa.Index(
        "idx_calendar_event_deleted",
        "is_deleted",
        postgresql_where=sa.text("NOT is_deleted"),
    ),
)


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
    async def get_by_room(
        self,
        room_id: str,
        include_deleted: bool = False,
        start_after: datetime | None = None,
        end_before: datetime | None = None,
    ) -> list[CalendarEvent]:
        query = calendar_events.select().where(calendar_events.c.room_id == room_id)

        if not include_deleted:
            query = query.where(calendar_events.c.is_deleted == False)

        if start_after:
            query = query.where(calendar_events.c.start_time >= start_after)

        if end_before:
            query = query.where(calendar_events.c.end_time <= end_before)

        query = query.order_by(calendar_events.c.start_time.asc())

        results = await get_database().fetch_all(query)
        return [CalendarEvent(**result) for result in results]

    async def get_upcoming(
        self, room_id: str, minutes_ahead: int = 120
    ) -> list[CalendarEvent]:
        """Get upcoming events for a room within the specified minutes, including currently happening events."""
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(minutes=minutes_ahead)

        query = (
            calendar_events.select()
            .where(
                sa.and_(
                    calendar_events.c.room_id == room_id,
                    calendar_events.c.is_deleted == False,
                    calendar_events.c.start_time <= future_time,
                    calendar_events.c.end_time >= now,
                )
            )
            .order_by(calendar_events.c.start_time.asc())
        )

        results = await get_database().fetch_all(query)
        return [CalendarEvent(**result) for result in results]

    async def get_upcoming_for_rooms(
        self, room_ids: list[str], minutes_ahead: int = 120
    ) -> list[CalendarEvent]:
        now = datetime.now(timezone.utc)
        future_time = now + timedelta(minutes=minutes_ahead)
        query = (
            calendar_events.select()
            .where(
                sa.and_(
                    calendar_events.c.room_id.in_(room_ids),
                    calendar_events.c.is_deleted == False,
                    calendar_events.c.start_time <= future_time,
                    calendar_events.c.end_time >= now,
                )
            )
            .order_by(calendar_events.c.start_time.asc())
        )
        results = await get_database().fetch_all(query)
        return [CalendarEvent(**result) for result in results]

    async def get_by_id(self, event_id: str) -> CalendarEvent | None:
        query = calendar_events.select().where(calendar_events.c.id == event_id)
        result = await get_database().fetch_one(query)
        return CalendarEvent(**result) if result else None

    async def get_by_ics_uid(self, room_id: str, ics_uid: str) -> CalendarEvent | None:
        query = calendar_events.select().where(
            sa.and_(
                calendar_events.c.room_id == room_id,
                calendar_events.c.ics_uid == ics_uid,
            )
        )
        result = await get_database().fetch_one(query)
        return CalendarEvent(**result) if result else None

    async def upsert(self, event: CalendarEvent) -> CalendarEvent:
        existing = await self.get_by_ics_uid(event.room_id, event.ics_uid)

        if existing:
            event.id = existing.id
            event.created_at = existing.created_at
            event.updated_at = datetime.now(timezone.utc)

            query = (
                calendar_events.update()
                .where(calendar_events.c.id == existing.id)
                .values(**event.model_dump())
            )
        else:
            query = calendar_events.insert().values(**event.model_dump())

        await get_database().execute(query)
        return event

    async def soft_delete_missing(
        self, room_id: str, current_ics_uids: list[str]
    ) -> int:
        """Soft delete future events that are no longer in the calendar."""
        now = datetime.now(timezone.utc)

        select_query = calendar_events.select().where(
            sa.and_(
                calendar_events.c.room_id == room_id,
                calendar_events.c.start_time > now,
                calendar_events.c.is_deleted == False,
                calendar_events.c.ics_uid.notin_(current_ics_uids)
                if current_ics_uids
                else True,
            )
        )

        to_delete = await get_database().fetch_all(select_query)
        delete_count = len(to_delete)

        if delete_count > 0:
            update_query = (
                calendar_events.update()
                .where(
                    sa.and_(
                        calendar_events.c.room_id == room_id,
                        calendar_events.c.start_time > now,
                        calendar_events.c.is_deleted == False,
                        calendar_events.c.ics_uid.notin_(current_ics_uids)
                        if current_ics_uids
                        else True,
                    )
                )
                .values(is_deleted=True, updated_at=now)
            )

            await get_database().execute(update_query)

        return delete_count

    async def delete_by_room(self, room_id: str) -> int:
        query = calendar_events.delete().where(calendar_events.c.room_id == room_id)
        result = await get_database().execute(query)
        return result.rowcount


calendar_events_controller = CalendarEventController()
