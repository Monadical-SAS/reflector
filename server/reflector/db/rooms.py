import secrets
from datetime import datetime, timezone
from sqlite3 import IntegrityError
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import or_

from reflector.db.base import RoomModel
from reflector.utils import generate_uuid4


class Room(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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
    recording_trigger: Literal[
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


class RoomController:
    async def get_all(
        self,
        session: AsyncSession,
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
        query = select(RoomModel)
        if user_id is not None:
            query = query.where(or_(RoomModel.user_id == user_id, RoomModel.is_shared))
        else:
            query = query.where(RoomModel.is_shared)

        if order_by is not None:
            field = getattr(RoomModel, order_by[1:])
            if order_by.startswith("-"):
                field = field.desc()
            query = query.order_by(field)

        if return_query:
            return query

        result = await session.execute(query)
        return [Room.model_validate(row) for row in result.scalars().all()]

    async def add(
        self,
        session: AsyncSession,
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
    ):
        """
        Add a new room
        """
        if webhook_url and not webhook_secret:
            webhook_secret = secrets.token_urlsafe(32)

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
            webhook_url=webhook_url,
            webhook_secret=webhook_secret,
            ics_url=ics_url,
            ics_fetch_interval=ics_fetch_interval,
            ics_enabled=ics_enabled,
        )
        new_room = RoomModel(**room.model_dump())
        session.add(new_room)
        try:
            await session.flush()
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Room name is not unique")
        return room

    async def update(
        self, session: AsyncSession, room: Room, values: dict, mutate=True
    ):
        """
        Update a room fields with key/values in values
        """
        if values.get("webhook_url") and not values.get("webhook_secret"):
            values["webhook_secret"] = secrets.token_urlsafe(32)

        query = update(RoomModel).where(RoomModel.id == room.id).values(**values)
        try:
            await session.execute(query)
            await session.flush()
        except IntegrityError:
            raise HTTPException(status_code=400, detail="Room name is not unique")

        if mutate:
            for key, value in values.items():
                setattr(room, key, value)

    async def get_by_id(
        self, session: AsyncSession, room_id: str, **kwargs
    ) -> Room | None:
        """
        Get a room by id
        """
        query = select(RoomModel).where(RoomModel.id == room_id)
        if "user_id" in kwargs:
            query = query.where(RoomModel.user_id == kwargs["user_id"])
        result = await session.execute(query)
        row = result.scalars().first()
        if not row:
            return None
        return Room.model_validate(row)

    async def get_by_name(
        self, session: AsyncSession, room_name: str, **kwargs
    ) -> Room | None:
        """
        Get a room by name
        """
        query = select(RoomModel).where(RoomModel.name == room_name)
        if "user_id" in kwargs:
            query = query.where(RoomModel.user_id == kwargs["user_id"])
        result = await session.execute(query)
        row = result.scalars().first()
        if not row:
            return None
        return Room.model_validate(row)

    async def get_by_id_for_http(
        self, session: AsyncSession, meeting_id: str, user_id: str | None
    ) -> Room:
        """
        Get a room by ID for HTTP request.

        If not found, it will raise a 404 error.
        """
        query = select(RoomModel).where(RoomModel.id == meeting_id)
        result = await session.execute(query)
        row = result.scalars().first()
        if not row:
            raise HTTPException(status_code=404, detail="Room not found")

        room = Room.model_validate(row)

        return room

    async def get_ics_enabled(self, session: AsyncSession) -> list[Room]:
        query = select(RoomModel).where(
            RoomModel.ics_enabled == True, RoomModel.ics_url != None
        )
        result = await session.execute(query)
        results = result.scalars().all()
        return [Room(**row.__dict__) for row in results]

    async def remove_by_id(
        self,
        session: AsyncSession,
        room_id: str,
        user_id: str | None = None,
    ) -> None:
        """
        Remove a room by id
        """
        room = await self.get_by_id(session, room_id, user_id=user_id)
        if not room:
            return
        if user_id is not None and room.user_id != user_id:
            return
        query = delete(RoomModel).where(RoomModel.id == room_id)
        await session.execute(query)
        await session.flush()


rooms_controller = RoomController()
