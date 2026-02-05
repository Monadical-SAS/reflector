import secrets
from datetime import datetime, timezone
from sqlite3 import IntegrityError
from typing import Literal

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.sql import false, or_

from reflector.db import get_database, metadata
from reflector.schemas.platform import Platform
from reflector.settings import settings
from reflector.utils import generate_uuid4

rooms = sqlalchemy.Table(
    "room",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String, nullable=False, unique=True),
    sqlalchemy.Column("user_id", sqlalchemy.String, nullable=False),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True), nullable=False),
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
    sqlalchemy.Column("webhook_url", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("webhook_secret", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("ics_url", sqlalchemy.Text),
    sqlalchemy.Column("ics_fetch_interval", sqlalchemy.Integer, server_default="300"),
    sqlalchemy.Column(
        "ics_enabled", sqlalchemy.Boolean, nullable=False, server_default=false()
    ),
    sqlalchemy.Column("ics_last_sync", sqlalchemy.DateTime(timezone=True)),
    sqlalchemy.Column("ics_last_etag", sqlalchemy.Text),
    sqlalchemy.Column(
        "platform",
        sqlalchemy.String,
        nullable=False,
    ),
    sqlalchemy.Column(
        "skip_consent",
        sqlalchemy.Boolean,
        nullable=False,
        server_default=sqlalchemy.sql.false(),
    ),
    sqlalchemy.Index("idx_room_is_shared", "is_shared"),
    sqlalchemy.Index("idx_room_ics_enabled", "ics_enabled"),
)


class Room(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    name: str
    user_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    zulip_auto_post: bool = False
    zulip_stream: str = ""
    zulip_topic: str = ""
    is_locked: bool = False
    room_mode: Literal["normal", "group"] = "normal"
    recording_type: Literal["none", "local", "cloud"] = "cloud"
    recording_trigger: Literal[  # whereby-specific
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    is_shared: bool = False
    webhook_url: str | None = None
    webhook_secret: str | None = None
    ics_url: str | None = None
    ics_fetch_interval: int = 300
    ics_enabled: bool = False
    ics_last_sync: datetime | None = None
    ics_last_etag: str | None = None
    platform: Platform = Field(default_factory=lambda: settings.DEFAULT_VIDEO_PLATFORM)
    skip_consent: bool = False


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

        results = await get_database().fetch_all(query)
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
        webhook_url: str = "",
        webhook_secret: str = "",
        ics_url: str | None = None,
        ics_fetch_interval: int = 300,
        ics_enabled: bool = False,
        platform: Platform = settings.DEFAULT_VIDEO_PLATFORM,
        skip_consent: bool = False,
    ):
        """
        Add a new room
        """
        if webhook_url and not webhook_secret:
            webhook_secret = secrets.token_urlsafe(32)

        room_data = {
            "name": name,
            "user_id": user_id,
            "zulip_auto_post": zulip_auto_post,
            "zulip_stream": zulip_stream,
            "zulip_topic": zulip_topic,
            "is_locked": is_locked,
            "room_mode": room_mode,
            "recording_type": recording_type,
            "recording_trigger": recording_trigger,
            "is_shared": is_shared,
            "webhook_url": webhook_url,
            "webhook_secret": webhook_secret,
            "ics_url": ics_url,
            "ics_fetch_interval": ics_fetch_interval,
            "ics_enabled": ics_enabled,
            "platform": platform,
            "skip_consent": skip_consent,
        }

        room = Room(**room_data)
        query = rooms.insert().values(**room.model_dump())
        try:
            await get_database().execute(query)
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Room name is not unique")
        return room

    async def update(self, room: Room, values: dict, mutate=True):
        """
        Update a room fields with key/values in values
        """
        if values.get("webhook_url") and not values.get("webhook_secret"):
            values["webhook_secret"] = secrets.token_urlsafe(32)

        query = rooms.update().where(rooms.c.id == room.id).values(**values)
        try:
            await get_database().execute(query)
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
        result = await get_database().fetch_one(query)
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
        result = await get_database().fetch_one(query)
        if not result:
            return None
        return Room(**result)

    async def get_by_id_for_http(self, meeting_id: str, user_id: str | None) -> Room:
        """
        Get a room by ID for HTTP request.

        If not found, it will raise a 404 error.
        """
        query = rooms.select().where(rooms.c.id == meeting_id)
        result = await get_database().fetch_one(query)
        if not result:
            raise HTTPException(status_code=404, detail="Room not found")

        room = Room(**result)

        return room

    async def get_ics_enabled(self) -> list[Room]:
        query = rooms.select().where(
            rooms.c.ics_enabled == True, rooms.c.ics_url != None
        )
        results = await get_database().fetch_all(query)
        return [Room(**result) for result in results]

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
        await get_database().execute(query)


rooms_controller = RoomController()
