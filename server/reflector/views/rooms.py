from datetime import datetime, timedelta
from typing import Annotated, Optional
import logging

import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from pydantic import BaseModel
from reflector.db import database
from reflector.db.meetings import Meeting, meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.settings import settings
from reflector.whereby import create_meeting, upload_logo
import asyncpg.exceptions
import sqlite3

logger = logging.getLogger(__name__)

router = APIRouter()


class Room(BaseModel):
    id: str
    name: str
    user_id: str
    created_at: datetime
    zulip_auto_post: bool
    zulip_stream: str
    zulip_topic: str
    is_locked: bool
    room_mode: str
    recording_type: str
    recording_trigger: str
    is_shared: bool


class CreateRoom(BaseModel):
    name: str
    zulip_auto_post: bool
    zulip_stream: str
    zulip_topic: str
    is_locked: bool
    room_mode: str
    recording_type: str
    recording_trigger: str
    is_shared: bool


class UpdateRoom(BaseModel):
    name: str
    zulip_auto_post: bool
    zulip_stream: str
    zulip_topic: str
    is_locked: bool
    room_mode: str
    recording_type: str
    recording_trigger: str
    is_shared: bool


class DeletionStatus(BaseModel):
    status: str


@router.get("/rooms", response_model=Page[Room])
async def rooms_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[Room]:
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    return await paginate(
        database,
        await rooms_controller.get_all(
            user_id=user_id, order_by="-created_at", return_query=True
        ),
    )


@router.post("/rooms", response_model=Room)
async def rooms_create(
    room: CreateRoom,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None

    return await rooms_controller.add(
        name=room.name,
        user_id=user_id,
        zulip_auto_post=room.zulip_auto_post,
        zulip_stream=room.zulip_stream,
        zulip_topic=room.zulip_topic,
        is_locked=room.is_locked,
        room_mode=room.room_mode,
        recording_type=room.recording_type,
        recording_trigger=room.recording_trigger,
        is_shared=room.is_shared,
    )


@router.patch("/rooms/{room_id}", response_model=Room)
async def rooms_update(
    room_id: str,
    info: UpdateRoom,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_id_for_http(room_id, user_id=user_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    values = info.dict(exclude_unset=True)
    await rooms_controller.update(room, values)
    return room


@router.delete("/rooms/{room_id}", response_model=DeletionStatus)
async def rooms_delete(
    room_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_id(room_id, user_id=user_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    await rooms_controller.remove_by_id(room.id, user_id=user_id)
    return DeletionStatus(status="ok")


@router.post("/rooms/{room_name}/meeting", response_model=Meeting)
async def rooms_create_meeting(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    current_time = datetime.utcnow()
    meeting = await meetings_controller.get_active(room=room, current_time=current_time)

    if meeting is None:
        end_date = current_time + timedelta(hours=8)

        # Create Whereby meeting first with proper error handling
        try:
            whereby_meeting = await create_meeting("", end_date=end_date, room=room)
        except Exception as e:
            logger.error(
                "Failed to create Whereby meeting for room %s: %s", room.name, str(e)
            )
            raise HTTPException(
                status_code=503,
                detail="Video conferencing service temporarily unavailable",
            )

        # Try to upload logo, but don't fail if it doesn't work
        try:
            await upload_logo(whereby_meeting["roomName"], "./images/logo.png")
        except Exception as e:
            # Log this but don't fail the request
            logger.warning(
                "Logo upload failed for meeting %s: %s",
                whereby_meeting["roomName"],
                str(e),
            )

        # Now try to save to database
        try:
            meeting = await meetings_controller.create(
                id=whereby_meeting["meetingId"],
                room_name=whereby_meeting["roomName"],
                room_url=whereby_meeting["roomUrl"],
                host_room_url=whereby_meeting["hostRoomUrl"],
                start_date=datetime.fromisoformat(whereby_meeting["startDate"]),
                end_date=datetime.fromisoformat(whereby_meeting["endDate"]),
                user_id=user_id,
                room=room,
            )
        except (asyncpg.exceptions.UniqueViolationError, sqlite3.IntegrityError):
            # Another request already created a meeting for this room
            # Log this race condition occurrence
            logger.info(
                "Race condition detected for room %s - fetching existing meeting",
                room.name,
            )
            logger.warning(
                "Whereby meeting %s was created but not used (resource leak) for room %s",
                whereby_meeting["meetingId"],
                room.name,
            )

            # Fetch the meeting that was created by the other request
            meeting = await meetings_controller.get_active(
                room=room, current_time=current_time
            )
            if meeting is None:
                # Edge case: meeting was created but expired/deleted between checks
                logger.error(
                    "Meeting disappeared after race condition for room %s", room.name
                )
                raise HTTPException(
                    status_code=503, detail="Unable to join meeting - please try again"
                )

    if user_id != room.user_id:
        meeting.host_room_url = ""

    return meeting
