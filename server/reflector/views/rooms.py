import logging
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Optional

import asyncpg.exceptions
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import apaginate
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db import get_database
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import VideoPlatform, rooms_controller
from reflector.settings import settings
from reflector.video_platforms.factory import (
    create_platform_client,
)
from reflector.worker.webhook import test_webhook

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_datetime_with_timezone(iso_string: str) -> datetime:
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


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
    platform: VideoPlatform = VideoPlatform.WHEREBY


class RoomDetails(Room):
    webhook_url: str | None
    webhook_secret: str | None


class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    start_date: datetime
    end_date: datetime
    recording_type: Literal["none", "local", "cloud"] = "cloud"


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
    webhook_url: str
    webhook_secret: str
    platform: VideoPlatform


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
    webhook_url: str
    webhook_secret: str
    platform: VideoPlatform


class DeletionStatus(BaseModel):
    status: str


class WebhookTestResult(BaseModel):
    success: bool
    message: str = ""
    error: str = ""
    status_code: int | None = None
    response_preview: str | None = None


@router.get("/rooms", response_model=Page[RoomDetails])
async def rooms_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[RoomDetails]:
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    return await apaginate(
        get_database(),
        await rooms_controller.get_all(
            user_id=user_id, order_by="-created_at", return_query=True
        ),
    )


@router.get("/rooms/{room_id}", response_model=RoomDetails)
async def rooms_get(
    room_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_id_for_http(room_id, user_id=user_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return room


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
        webhook_url=room.webhook_url,
        webhook_secret=room.webhook_secret,
        platform=room.platform,
    )


@router.patch("/rooms/{room_id}", response_model=RoomDetails)
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

    current_time = datetime.now(timezone.utc)
    meeting = await meetings_controller.get_active(room=room, current_time=current_time)

    if meeting is None:
        end_date = current_time + timedelta(hours=8)

        platform = room.platform
        client = create_platform_client(platform)

        platform_meeting = await client.create_meeting("", end_date=end_date, room=room)
        await client.upload_logo(platform_meeting.room_name, "./images/logo.png")

        meeting_data = {
            "meeting_id": platform_meeting.meeting_id,
            "room_name": platform_meeting.room_name,
            "room_url": platform_meeting.room_url,
            "host_room_url": platform_meeting.host_room_url,
            "start_date": current_time,
            "end_date": end_date,
        }
        try:
            meeting = await meetings_controller.create(
                id=meeting_data["meeting_id"],
                room_name=meeting_data["room_name"],
                room_url=meeting_data["room_url"],
                host_room_url=meeting_data["host_room_url"],
                start_date=meeting_data["start_date"],
                end_date=meeting_data["end_date"],
                user_id=user_id,
                room=room,
            )
        except (asyncpg.exceptions.UniqueViolationError, sqlite3.IntegrityError):
            logger.info(
                "Race condition detected for room %s - fetching existing meeting",
                room.name,
            )
            logger.warning(
                "Platform meeting %s was created but not used (resource leak) for room %s",
                meeting_data["meeting_id"],
                room.name,
            )
            meeting = await meetings_controller.get_active(
                room=room, current_time=current_time
            )
            if meeting is None:
                logger.error(
                    "Meeting disappeared after race condition for room %s",
                    room.name,
                    exc_info=True,
                )
                raise HTTPException(
                    status_code=503, detail="Unable to join meeting - please try again"
                )

    if user_id != room.user_id:
        meeting.host_room_url = ""

    return meeting


@router.post("/rooms/{room_id}/webhook/test", response_model=WebhookTestResult)
async def rooms_test_webhook(
    room_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None

    room = await rooms_controller.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if user_id and room.user_id != user_id:
        raise HTTPException(
            status_code=403, detail="Not authorized to test this room's webhook"
        )

    result = await test_webhook(room_id)
    return WebhookTestResult(**result)
