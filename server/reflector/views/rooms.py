import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.sqlalchemy import paginate
from pydantic import BaseModel
from redis.exceptions import LockError

import reflector.auth as auth
from reflector.db import get_session_factory
from reflector.db.calendar_events import calendar_events_controller
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.redis_cache import RedisAsyncLock
from reflector.services.ics_sync import ics_sync_service
from reflector.settings import settings
from reflector.whereby import create_meeting, upload_logo
from reflector.worker.webhook import test_webhook

logger = logging.getLogger(__name__)


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


class RoomDetails(Room):
    webhook_url: str | None
    webhook_secret: str | None


class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    # TODO it's not always present, | None
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
    is_active: bool = True
    calendar_event_id: str | None = None
    calendar_metadata: dict[str, Any] | None = None


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
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None
    ics_url: Optional[str] = None
    ics_fetch_interval: Optional[int] = None
    ics_enabled: Optional[bool] = None


class CreateRoomMeeting(BaseModel):
    allow_duplicated: Optional[bool] = False


class DeletionStatus(BaseModel):
    status: str


class WebhookTestResult(BaseModel):
    success: bool
    message: str = ""
    error: str = ""
    status_code: int | None = None
    response_preview: str | None = None


class ICSStatus(BaseModel):
    status: Literal["enabled", "disabled"]
    last_sync: Optional[datetime] = None
    next_sync: Optional[datetime] = None
    last_etag: Optional[str] = None
    events_count: int = 0


class SyncStatus(str, Enum):
    success = "success"
    unchanged = "unchanged"
    error = "error"
    skipped = "skipped"


class ICSSyncResult(BaseModel):
    status: SyncStatus
    hash: Optional[str] = None
    events_found: int = 0
    total_events: int = 0
    events_created: int = 0
    events_updated: int = 0
    events_deleted: int = 0
    error: Optional[str] = None
    reason: Optional[str] = None


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


router = APIRouter()


def parse_datetime_with_timezone(iso_string: str) -> datetime:
    """Parse ISO datetime string and ensure timezone awareness (defaults to UTC if naive)."""
    dt = datetime.fromisoformat(iso_string)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


@router.get("/rooms", response_model=Page[RoomDetails])
async def rooms_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[RoomDetails]:
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    session_factory = get_session_factory()
    async with session_factory() as session:
        query = await rooms_controller.get_all(
            user_id=user_id, order_by="-created_at", return_query=True
        )
        return await paginate(session, query)


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


@router.get("/rooms/name/{room_name}", response_model=RoomDetails)
async def rooms_get_by_name(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Convert to RoomDetails format (add webhook fields if user is owner)
    room_dict = room.__dict__.copy()
    if user_id == room.user_id:
        # User is owner, include webhook details if available
        room_dict["webhook_url"] = getattr(room, "webhook_url", None)
        room_dict["webhook_secret"] = getattr(room, "webhook_secret", None)
    else:
        # Non-owner, hide webhook details
        room_dict["webhook_url"] = None
        room_dict["webhook_secret"] = None

    return RoomDetails(**room_dict)


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
        ics_url=room.ics_url,
        ics_fetch_interval=room.ics_fetch_interval,
        ics_enabled=room.ics_enabled,
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
    info: CreateRoomMeeting,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    try:
        async with RedisAsyncLock(
            f"create_meeting:{room_name}",
            timeout=30,
            extend_interval=10,
            blocking_timeout=5.0,
        ) as lock:
            current_time = datetime.now(timezone.utc)

            meeting = None
            if not info.allow_duplicated:
                meeting = await meetings_controller.get_active(
                    room=room, current_time=current_time
                )

            if meeting is None:
                end_date = current_time + timedelta(hours=8)

                whereby_meeting = await create_meeting("", end_date=end_date, room=room)

                await upload_logo(whereby_meeting["roomName"], "./images/logo.png")

                meeting = await meetings_controller.create(
                    id=whereby_meeting["meetingId"],
                    room_name=whereby_meeting["roomName"],
                    room_url=whereby_meeting["roomUrl"],
                    host_room_url=whereby_meeting["hostRoomUrl"],
                    start_date=parse_datetime_with_timezone(
                        whereby_meeting["startDate"]
                    ),
                    end_date=parse_datetime_with_timezone(whereby_meeting["endDate"]),
                    room=room,
                )
    except LockError:
        logger.warning("Failed to acquire lock for room %s within timeout", room_name)
        raise HTTPException(
            status_code=503, detail="Meeting creation in progress, please try again"
        )

    if user_id != room.user_id:
        meeting.host_room_url = ""

    return meeting


@router.post("/rooms/{room_id}/webhook/test", response_model=WebhookTestResult)
async def rooms_test_webhook(
    room_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    """Test webhook configuration by sending a sample payload."""
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


@router.get("/rooms/{room_name}/meetings", response_model=list[CalendarEventResponse])
async def rooms_list_meetings(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

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
    minutes_ahead: int = 120,
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    events = await calendar_events_controller.get_upcoming(
        room.id, minutes_ahead=minutes_ahead
    )

    if user_id != room.user_id:
        for event in events:
            event.description = None
            event.attendees = None

    return events


@router.get("/rooms/{room_name}/meetings/active", response_model=list[Meeting])
async def rooms_list_active_meetings(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    current_time = datetime.now(timezone.utc)
    meetings = await meetings_controller.get_all_active_for_room(
        room=room, current_time=current_time
    )

    # Hide host URLs from non-owners
    if user_id != room.user_id:
        for meeting in meetings:
            meeting.host_room_url = ""

    return meetings


@router.get("/rooms/{room_name}/meetings/{meeting_id}", response_model=Meeting)
async def rooms_get_meeting(
    room_name: str,
    meeting_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    """Get a single meeting by ID within a specific room."""
    user_id = user["sub"] if user else None

    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.room_id != room.id:
        raise HTTPException(
            status_code=403, detail="Meeting does not belong to this room"
        )

    if user_id != room.user_id and not room.is_shared:
        meeting.host_room_url = ""

    return meeting


@router.post("/rooms/{room_name}/meetings/{meeting_id}/join", response_model=Meeting)
async def rooms_join_meeting(
    room_name: str,
    meeting_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    meeting = await meetings_controller.get_by_id(meeting_id)

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if meeting.room_id != room.id:
        raise HTTPException(
            status_code=403, detail="Meeting does not belong to this room"
        )

    if not meeting.is_active:
        raise HTTPException(status_code=400, detail="Meeting is not active")

    current_time = datetime.now(timezone.utc)
    if meeting.end_date <= current_time:
        raise HTTPException(status_code=400, detail="Meeting has ended")

    # Hide host URL from non-owners
    if user_id != room.user_id:
        meeting.host_room_url = ""

    return meeting
