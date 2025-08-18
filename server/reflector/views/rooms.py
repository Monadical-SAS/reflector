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
from reflector.db.rooms import rooms_controller
from reflector.settings import settings
from reflector.whereby import create_meeting, upload_logo

logger = logging.getLogger(__name__)

router = APIRouter()


def parse_datetime_with_timezone(iso_string: str) -> datetime:
    """Parse ISO datetime string and ensure timezone awareness (defaults to UTC if naive)."""
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
    ics_url: Optional[str] = None
    ics_fetch_interval: int = 300
    ics_enabled: bool = False
    ics_last_sync: Optional[datetime] = None
    ics_last_etag: Optional[str] = None


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
    ics_url: Optional[str] = None
    ics_fetch_interval: int = 300
    ics_enabled: bool = False


class UpdateRoom(BaseModel):
    name: Optional[str] = None
    zulip_auto_post: Optional[bool] = None
    zulip_stream: Optional[str] = None
    zulip_topic: Optional[str] = None
    is_locked: Optional[bool] = None
    room_mode: Optional[str] = None
    recording_type: Optional[str] = None
    recording_trigger: Optional[str] = None
    is_shared: Optional[bool] = None
    ics_url: Optional[str] = None
    ics_fetch_interval: Optional[int] = None
    ics_enabled: Optional[bool] = None


class DeletionStatus(BaseModel):
    status: str


@router.get("/rooms", response_model=Page[Room])
async def rooms_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[Room]:
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    return await apaginate(
        get_database(),
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
        ics_url=room.ics_url,
        ics_fetch_interval=room.ics_fetch_interval,
        ics_enabled=room.ics_enabled,
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

    current_time = datetime.now(timezone.utc)
    meeting = await meetings_controller.get_active(room=room, current_time=current_time)

    if meeting is None:
        end_date = current_time + timedelta(hours=8)

        whereby_meeting = await create_meeting("", end_date=end_date, room=room)
        await upload_logo(whereby_meeting["roomName"], "./images/logo.png")

        # Now try to save to database
        try:
            meeting = await meetings_controller.create(
                id=whereby_meeting["meetingId"],
                room_name=whereby_meeting["roomName"],
                room_url=whereby_meeting["roomUrl"],
                host_room_url=whereby_meeting["hostRoomUrl"],
                start_date=parse_datetime_with_timezone(whereby_meeting["startDate"]),
                end_date=parse_datetime_with_timezone(whereby_meeting["endDate"]),
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


class ICSStatus(BaseModel):
    status: str
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    last_etag: Optional[str] = None
    events_count: int = 0


class ICSSyncResult(BaseModel):
    status: str
    hash: Optional[str] = None
    events_found: int = 0
    events_created: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    error: Optional[str] = None


@router.post("/rooms/{room_name}/ics/sync", response_model=ICSSyncResult)
async def rooms_sync_ics(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if user_id != room.user_id:
        raise HTTPException(
            status_code=403, detail="Only room owner can trigger ICS sync"
        )

    if not room.ics_enabled or not room.ics_url:
        raise HTTPException(status_code=400, detail="ICS not configured for this room")

    from reflector.services.ics_sync import ics_sync_service

    result = await ics_sync_service.sync_room_calendar(room)

    if result["status"] == "error":
        raise HTTPException(
            status_code=500, detail=result.get("error", "Unknown error")
        )

    return ICSSyncResult(**result)


@router.get("/rooms/{room_name}/ics/status", response_model=ICSStatus)
async def rooms_ics_status(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if user_id != room.user_id:
        raise HTTPException(
            status_code=403, detail="Only room owner can view ICS status"
        )

    next_sync = None
    if room.ics_enabled and room.ics_last_sync:
        next_sync = room.ics_last_sync + timedelta(seconds=room.ics_fetch_interval)

    from reflector.db.calendar_events import calendar_events_controller

    events = await calendar_events_controller.get_by_room(
        room.id, include_deleted=False
    )

    return ICSStatus(
        status="enabled" if room.ics_enabled else "disabled",
        last_sync=room.ics_last_sync,
        next_sync=next_sync,
        last_etag=room.ics_last_etag,
        events_count=len(events),
    )


class CalendarEventResponse(BaseModel):
    id: str
    room_id: str
    ics_uid: str
    title: Optional[str] = None
    description: Optional[str] = None
    start_time: datetime
    end_time: datetime
    attendees: Optional[list[dict]] = None
    location: Optional[str] = None
    last_synced: datetime
    created_at: datetime
    updated_at: datetime


@router.get("/rooms/{room_name}/meetings", response_model=list[CalendarEventResponse])
async def rooms_list_meetings(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    from reflector.db.calendar_events import calendar_events_controller

    events = await calendar_events_controller.get_by_room(
        room.id, include_deleted=False
    )

    if user_id != room.user_id:
        for event in events:
            event.description = None
            event.attendees = None

    return events


@router.get(
    "/rooms/{room_name}/meetings/upcoming", response_model=list[CalendarEventResponse]
)
async def rooms_list_upcoming_meetings(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    minutes_ahead: int = 30,
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    from reflector.db.calendar_events import calendar_events_controller

    events = await calendar_events_controller.get_upcoming(
        room.id, minutes_ahead=minutes_ahead
    )

    if user_id != room.user_id:
        for event in events:
            event.description = None
            event.attendees = None

    return events
