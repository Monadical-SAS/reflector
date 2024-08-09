from datetime import datetime

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel
from reflector.db import database, metadata

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
)


class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    viewer_room_url: str
    start_date: datetime
    end_date: datetime
    user_id: str


class MeetingController:
    async def add(
        self,
        id: str,
        room_name: str,
        room_url: str,
        host_room_url: str,
        viewer_room_url: str,
        start_date: datetime,
        end_date: datetime,
        user_id: str,
    ):
        """
        Add a new meeting
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
