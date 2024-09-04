from datetime import datetime, timezone
from typing import Literal

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel
from reflector.db import database, metadata
from reflector.db.rooms import Room
from sqlalchemy.sql import false

meetings = sqlalchemy.Table(
    "meeting",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("room_name", sqlalchemy.String),
    sqlalchemy.Column("room_url", sqlalchemy.String),
    sqlalchemy.Column("host_room_url", sqlalchemy.String),
    sqlalchemy.Column("viewer_room_url", sqlalchemy.String),
    sqlalchemy.Column("start_date", sqlalchemy.DateTime),
    sqlalchemy.Column("end_date", sqlalchemy.DateTime),
    sqlalchemy.Column("user_id", sqlalchemy.String),
    sqlalchemy.Column("room_id", sqlalchemy.String),
    sqlalchemy.Column(
        "is_locked", sqlalchemy.Boolean, nullable=False, server_default=false()
    ),
    sqlalchemy.Column(
        "room_mode", sqlalchemy.String, nullable=False, server_default="normal"
    ),
    sqlalchemy.Column(
        "recording_type", sqlalchemy.String, nullable=False, server_default="cloud"
    ),
    sqlalchemy.Column(
        "recording_trigger",
        sqlalchemy.String,
        nullable=False,
        server_default="automatic-2nd-participant",
    ),
)


class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    viewer_room_url: str
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


class MeetingController:
    async def create(
        self,
        id: str,
        room_name: str,
        room_url: str,
        host_room_url: str,
        viewer_room_url: str,
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
            viewer_room_url=viewer_room_url,
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

    async def get_latest(self, room: Room) -> Meeting:
        """
        Get latest meeting for a room.
        """
        end_date = getattr(meetings.c, "end_date")
        query = (
            meetings.select()
            .where(
                sqlalchemy.and_(
                    meetings.c.room_id == room.id,
                    meetings.c.is_locked == room.is_locked,
                    meetings.c.room_mode == room.room_mode,
                    meetings.c.recording_type == room.recording_type,
                    meetings.c.recording_trigger == room.recording_trigger,
                    meetings.c.end_date > datetime.now(timezone.utc),
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


meetings_controller = MeetingController()
