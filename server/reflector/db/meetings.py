from datetime import datetime
from typing import Literal

import sqlalchemy as sa
from fastapi import HTTPException
from pydantic import BaseModel
from reflector.db import database, metadata
from reflector.db.rooms import Room

meetings = sa.Table(
    "meeting",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("room_name", sa.String),
    sa.Column("room_url", sa.String),
    sa.Column("host_room_url", sa.String),
    sa.Column("start_date", sa.DateTime),
    sa.Column("end_date", sa.DateTime),
    sa.Column("user_id", sa.String),
    sa.Column("room_id", sa.String),
    sa.Column("is_locked", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("room_mode", sa.String, nullable=False, server_default="normal"),
    sa.Column("recording_type", sa.String, nullable=False, server_default="cloud"),
    sa.Column(
        "recording_trigger",
        sa.String,
        nullable=False,
        server_default="automatic-2nd-participant",
    ),
    sa.Column(
        "num_clients",
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    ),
    sa.Column(
        "is_active",
        sa.Boolean,
        nullable=False,
        server_default=sa.true(),
    ),
    sa.Column(
        "last_active_ping",
        sa.DateTime,
        nullable=True,
    ),
)


class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    start_date: datetime
    end_date: datetime
    user_id: str | None = None
    room_id: str | None = None
    is_locked: bool = False
    room_mode: Literal["normal", "group"] = "normal"
    recording_type: Literal["none", "local", "cloud"] = "cloud"
    recording_trigger: Literal[
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    num_clients: int = 0
    last_active_ping: datetime | None = None


class MeetingController:
    async def create(
        self,
        id: str,
        room_name: str,
        room_url: str,
        host_room_url: str,
        start_date: datetime,
        end_date: datetime,
        user_id: str,
        room: Room,
    ):
        """
        Create a new meeting
        """
        meeting = Meeting(
            id=id,
            room_name=room_name,
            room_url=room_url,
            host_room_url=host_room_url,
            start_date=start_date,
            end_date=end_date,
            user_id=user_id,
            room_id=room.id,
            is_locked=room.is_locked,
            room_mode=room.room_mode,
            recording_type=room.recording_type,
            recording_trigger=room.recording_trigger,
        )
        query = meetings.insert().values(**meeting.model_dump())
        await database.execute(query)
        return meeting

    async def get_all_active(self) -> list[Meeting]:
        """
        Get active meetings.
        """
        query = meetings.select().where(meetings.c.is_active)
        return await database.fetch_all(query)

    async def get_by_room_name(
        self,
        room_name: str,
    ) -> Meeting:
        """
        Get a meeting by room name.
        """
        query = meetings.select().where(meetings.c.room_name == room_name)
        result = await database.fetch_one(query)
        if not result:
            return None

        return Meeting(**result)

    async def get_active(self, room: Room, current_time: datetime) -> Meeting:
        """
        Get latest meeting for a room.
        """
        end_date = getattr(meetings.c, "end_date")
        query = (
            meetings.select()
            .where(
                sa.and_(
                    meetings.c.room_id == room.id,
                    meetings.c.is_active,
                    meetings.c.end_date > current_time,
                )
            )
            .order_by(end_date.desc())
        )
        result = await database.fetch_one(query)
        if not result:
            return None

        return Meeting(**result)

    async def get_by_id(self, meeting_id: str, **kwargs) -> Meeting | None:
        """
        Get a meeting by id
        """
        query = meetings.select().where(meetings.c.id == meeting_id)
        result = await database.fetch_one(query)
        if not result:
            return None
        return Meeting(**result)

    async def get_by_id_for_http(self, meeting_id: str, user_id: str | None) -> Meeting:
        """
        Get a meeting by ID for HTTP request.

        If not found, it will raise a 404 error.
        """
        query = meetings.select().where(meetings.c.id == meeting_id)
        result = await database.fetch_one(query)
        if not result:
            raise HTTPException(status_code=404, detail="Meeting not found")

        meeting = Meeting(**result)
        if result["user_id"] != user_id:
            meeting.host_room_url = ""

        return meeting

    async def update_meeting(self, meeting_id: str, **kwargs):
        query = meetings.update().where(meetings.c.id == meeting_id).values(**kwargs)
        await database.execute(query)


meetings_controller = MeetingController()
