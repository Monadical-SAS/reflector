from datetime import datetime
from sqlite3 import IntegrityError
from typing import Literal

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.sql import false, or_

from reflector.db import database, metadata
from reflector.utils import generate_uuid4

rooms = sqlalchemy.Table(
    "room",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("user_id", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime, nullable=False),
    sqlalchemy.Column(
        "zulip_auto_post", sqlalchemy.Boolean, nullable=False, server_default=false()
    ),
    sqlalchemy.Column("zulip_stream", sqlalchemy.String),
    sqlalchemy.Column("zulip_topic", sqlalchemy.String),
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
    sqlalchemy.Column(
        "is_shared", sqlalchemy.Boolean, nullable=False, server_default=false()
    ),
    sqlalchemy.Column(
        "platform", sqlalchemy.String, nullable=False, server_default="whereby"
    ),
    sqlalchemy.Index("idx_room_is_shared", "is_shared"),
)


class Room(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    name: str
    user_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    zulip_auto_post: bool = False
    zulip_stream: str = ""
    zulip_topic: str = ""
    is_locked: bool = False
    room_mode: Literal["normal", "group"] = "normal"
    recording_type: Literal["none", "local", "cloud"] = "cloud"
    recording_trigger: Literal[
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    is_shared: bool = False
    platform: Literal["whereby", "daily"] = "whereby"


class RoomController:
    async def get_all(
        self,
        user_id: str | None = None,
        order_by: str | None = None,
        return_query: bool = False,
    ) -> list[Room]:
        """
        Get all rooms

        If `user_id` is specified, only return rooms that belong to the user.
        Otherwise, return all rooms.

        Parameters:
        - `order_by`: field to order by, e.g. "-created_at"
        """
        query = rooms.select()
        if user_id is not None:
            query = query.where(or_(rooms.c.user_id == user_id, rooms.c.is_shared))
        else:
            query = query.where(rooms.c.is_shared)

        if order_by is not None:
            field = getattr(rooms.c, order_by[1:])
            if order_by.startswith("-"):
                field = field.desc()
            query = query.order_by(field)

        if return_query:
            return query

        results = await database.fetch_all(query)
        return results

    async def add(
        self,
        name: str,
        user_id: str,
        zulip_auto_post: bool,
        zulip_stream: str,
        zulip_topic: str,
        is_locked: bool,
        room_mode: str,
        recording_type: str,
        recording_trigger: str,
        is_shared: bool,
        platform: str = "whereby",
    ):
        """
        Add a new room
        """
        room = Room(
            name=name,
            user_id=user_id,
            zulip_auto_post=zulip_auto_post,
            zulip_stream=zulip_stream,
            zulip_topic=zulip_topic,
            is_locked=is_locked,
            room_mode=room_mode,
            recording_type=recording_type,
            recording_trigger=recording_trigger,
            is_shared=is_shared,
            platform=platform,
        )
        query = rooms.insert().values(**room.model_dump())
        try:
            await database.execute(query)
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Room name is not unique")
        return room

    async def update(self, room: Room, values: dict, mutate=True):
        """
        Update a room fields with key/values in values
        """
        query = rooms.update().where(rooms.c.id == room.id).values(**values)
        try:
            await database.execute(query)
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Room name is not unique")

        if mutate:
            for key, value in values.items():
                setattr(room, key, value)

    async def get_by_id(self, room_id: str, **kwargs) -> Room | None:
        """
        Get a room by id
        """
        query = rooms.select().where(rooms.c.id == room_id)
        if "user_id" in kwargs:
            query = query.where(rooms.c.user_id == kwargs["user_id"])
        result = await database.fetch_one(query)
        if not result:
            return None
        return Room(**result)

    async def get_by_name(self, room_name: str, **kwargs) -> Room | None:
        """
        Get a room by name
        """
        query = rooms.select().where(rooms.c.name == room_name)
        if "user_id" in kwargs:
            query = query.where(rooms.c.user_id == kwargs["user_id"])
        result = await database.fetch_one(query)
        if not result:
            return None
        return Room(**result)

    async def get_by_id_for_http(self, meeting_id: str, user_id: str | None) -> Room:
        """
        Get a room by ID for HTTP request.

        If not found, it will raise a 404 error.
        """
        query = rooms.select().where(rooms.c.id == meeting_id)
        result = await database.fetch_one(query)
        if not result:
            raise HTTPException(status_code=404, detail="Room not found")

        room = Room(**result)

        return room

    async def remove_by_id(
        self,
        room_id: str,
        user_id: str | None = None,
    ) -> None:
        """
        Remove a room by id
        """
        room = await self.get_by_id(room_id, user_id=user_id)
        if not room:
            return
        if user_id is not None and room.user_id != user_id:
            return
        query = rooms.delete().where(rooms.c.id == room_id)
        await database.execute(query)


rooms_controller = RoomController()
