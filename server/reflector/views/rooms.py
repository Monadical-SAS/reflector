import json
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Annotated, Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import apaginate
from pydantic import BaseModel
from redis.exceptions import LockError

import reflector.auth as auth
from reflector.db import get_database
from reflector.db.calendar_events import calendar_events_controller
from reflector.db.daily_participant_sessions import (
    DailyParticipantSession,
    daily_participant_sessions_controller,
)
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.logger import logger
from reflector.presence.pending_joins import create_pending_join, delete_pending_join
from reflector.redis_cache import RedisAsyncLock, get_async_redis_client
from reflector.schemas.platform import Platform
from reflector.services.ics_sync import ics_sync_service
from reflector.settings import settings
from reflector.utils.string import NonEmptyString
from reflector.utils.url import add_query_param
from reflector.video_platforms.factory import create_platform_client
from reflector.worker.process import poll_daily_room_presence_task
from reflector.worker.webhook import test_webhook


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
    platform: Platform
    skip_consent: bool = False


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
    platform: Platform
    daily_composed_video_s3_key: str | None = None
    daily_composed_video_duration: int | None = None


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
    platform: Platform
    skip_consent: bool = False


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
    platform: Optional[Platform] = None
    skip_consent: Optional[bool] = None


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


@router.get("/rooms", response_model=Page[RoomDetails])
async def rooms_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[RoomDetails]:
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    paginated = await apaginate(
        get_database(),
        await rooms_controller.get_all(
            user_id=user_id, order_by="-created_at", return_query=True
        ),
    )

    return paginated


@router.get("/rooms/{room_id}", response_model=RoomDetails)
async def rooms_get(
    room_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_id_for_http(room_id, user_id=user_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if not room.is_shared and (user_id is None or room.user_id != user_id):
        raise HTTPException(status_code=403, detail="Room access denied")
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

    room_dict = room.__dict__.copy()
    if user_id == room.user_id:
        room_dict["webhook_url"] = getattr(room, "webhook_url", None)
        room_dict["webhook_secret"] = getattr(room, "webhook_secret", None)
    else:
        room_dict["webhook_url"] = None
        room_dict["webhook_secret"] = None

    return RoomDetails(**room_dict)


@router.post("/rooms", response_model=Room)
async def rooms_create(
    room: CreateRoom,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]

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
        platform=room.platform,
        skip_consent=room.skip_consent,
    )


@router.patch("/rooms/{room_id}", response_model=RoomDetails)
async def rooms_update(
    room_id: str,
    info: UpdateRoom,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]
    room = await rooms_controller.get_by_id_for_http(room_id, user_id=user_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    values = info.dict(exclude_unset=True)
    await rooms_controller.update(room, values)
    return room


@router.delete("/rooms/{room_id}", response_model=DeletionStatus)
async def rooms_delete(
    room_id: str,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]
    room = await rooms_controller.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")
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

                if meeting is not None:
                    settings_match = (
                        meeting.is_locked == room.is_locked
                        and meeting.room_mode == room.room_mode
                        and meeting.recording_type == room.recording_type
                        and meeting.recording_trigger == room.recording_trigger
                        and meeting.platform == room.platform
                    )
                    if not settings_match:
                        logger.info(
                            f"Room settings changed for {room_name}, creating new meeting",
                            room_id=room.id,
                            old_meeting_id=meeting.id,
                        )
                        meeting = None

            if meeting is None:
                end_date = current_time + timedelta(hours=8)

                platform = room.platform
                client = create_platform_client(platform)

                meeting_data = await client.create_meeting(
                    room.name, end_date=end_date, room=room
                )

                await client.upload_logo(meeting_data.room_name, "./images/logo.png")

                meeting = await meetings_controller.create(
                    id=meeting_data.meeting_id,
                    room_name=meeting_data.room_name,
                    room_url=meeting_data.room_url,
                    host_room_url=meeting_data.host_room_url,
                    start_date=current_time,
                    end_date=end_date,
                    room=room,
                )
    except LockError:
        logger.warning("Failed to acquire lock for room %s within timeout", room_name)
        raise HTTPException(
            status_code=503, detail="Meeting creation in progress, please try again"
        )

    if user_id != room.user_id and meeting.platform == "whereby":
        meeting.host_room_url = ""

    return meeting


@router.post("/rooms/{room_id}/webhook/test", response_model=WebhookTestResult)
async def rooms_test_webhook(
    room_id: str,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    """Test webhook configuration by sending a sample payload."""
    user_id = user["sub"]

    room = await rooms_controller.get_by_id(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.user_id != user_id:
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

    for meeting in meetings:
        meeting.platform = room.platform

    if user_id != room.user_id:
        for meeting in meetings:
            if meeting.platform == "whereby":
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

    meeting = await meetings_controller.get_by_id(meeting_id, room=room)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if user_id != room.user_id and not room.is_shared and meeting.platform == "whereby":
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

    meeting = await meetings_controller.get_by_id(meeting_id, room=room)

    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.is_active:
        raise HTTPException(status_code=400, detail="Meeting is not active")

    current_time = datetime.now(timezone.utc)
    if meeting.end_date <= current_time:
        raise HTTPException(status_code=400, detail="Meeting has ended")

    if meeting.platform == "daily" and user_id is not None:
        client = create_platform_client(meeting.platform)
        # Show Daily's built-in recording UI when:
        # - local recording (user controls when to record), OR
        # - cloud recording with consent disabled (skip_consent=True)
        # Hide it when cloud recording with consent enabled (we show custom consent UI)
        enable_recording_ui = meeting.recording_type == "local" or (
            meeting.recording_type == "cloud" and room.skip_consent
        )
        end_date = meeting.end_date
        if end_date.tzinfo is None:
            end_date = end_date.replace(tzinfo=timezone.utc)
        remaining_seconds = min(
            3 * 60 * 60, int((end_date - current_time).total_seconds())
        )
        token = await client.create_meeting_token(
            meeting.room_name,
            enable_recording_ui=enable_recording_ui,
            user_id=user_id,
            is_owner=user_id == room.user_id,
            max_recording_duration_seconds=remaining_seconds,
        )
        meeting = meeting.model_copy()
        meeting.room_url = add_query_param(meeting.room_url, "t", token)

    return meeting


class JoiningRequest(BaseModel):
    """Request body for /joining endpoint (before WebRTC handshake)."""

    connection_id: NonEmptyString
    """Unique identifier for this connection. Generated by client via crypto.randomUUID()."""


class JoiningResponse(BaseModel):
    status: Literal["ok"]


class JoinedRequest(BaseModel):
    """Request body for /joined endpoint (after WebRTC connection established)."""

    connection_id: NonEmptyString
    """Must match the connection_id sent to /joining."""

    session_id: NonEmptyString | None = None
    """Daily.co session_id for direct session creation. Optional for backward compat."""

    user_name: str | None = None
    """Display name from Daily.co participant data."""


class JoinedResponse(BaseModel):
    status: Literal["ok"]


def _get_pending_join_key(
    user: Optional[auth.UserInfo], connection_id: NonEmptyString
) -> str:
    """Get a unique key for pending join tracking.

    Uses user ID for authenticated users, connection_id for anonymous users.
    This ensures each browser tab has its own unique pending join record.
    """
    if user:
        return f"{user['sub']}:{connection_id}"
    return f"anon:{connection_id}"


@router.post(
    "/rooms/{room_name}/meetings/{meeting_id}/joining", response_model=JoiningResponse
)
async def meeting_joining(
    room_name: str,
    meeting_id: str,
    body: JoiningRequest,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> JoiningResponse:
    """Signal intent to join meeting. Called before WebRTC handshake starts.

    This creates a pending join record that prevents the meeting from being
    deactivated while the WebRTC handshake is in progress. The record expires
    automatically after 30 seconds if the connection is not established.
    """
    log = logger.bind(
        room_name=room_name, meeting_id=meeting_id, connection_id=body.connection_id
    )

    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    meeting = await meetings_controller.get_by_id(meeting_id, room=room)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.is_active:
        raise HTTPException(status_code=400, detail="Meeting is not active")

    join_key = _get_pending_join_key(user, body.connection_id)

    redis = await get_async_redis_client()
    try:
        await create_pending_join(redis, meeting_id, join_key)
        log.debug("Created pending join intent", join_key=join_key)
    finally:
        await redis.aclose()

    return JoiningResponse(status="ok")


@router.post(
    "/rooms/{room_name}/meetings/{meeting_id}/joined", response_model=JoinedResponse
)
async def meeting_joined(
    room_name: str,
    meeting_id: str,
    body: JoinedRequest,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> JoinedResponse:
    """Signal that WebRTC connection is established.

    This clears the pending join record, confirming the user has successfully
    connected to the meeting. Safe to call even if meeting was deactivated
    during the handshake (idempotent cleanup).
    """
    log = logger.bind(
        room_name=room_name, meeting_id=meeting_id, connection_id=body.connection_id
    )

    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    meeting = await meetings_controller.get_by_id(meeting_id, room=room)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Note: We don't check is_active here - the /joined call is a cleanup operation
    # and should succeed even if the meeting was deactivated during the handshake

    join_key = _get_pending_join_key(user, body.connection_id)

    redis = await get_async_redis_client()
    try:
        await delete_pending_join(redis, meeting_id, join_key)
        log.debug("Cleared pending join intent", join_key=join_key)
    finally:
        await redis.aclose()

    # Create session directly when session_id provided (instant presence update)
    if body.session_id and meeting.platform == "daily":
        session = DailyParticipantSession(
            id=f"{meeting.id}:{body.session_id}",
            meeting_id=meeting.id,
            room_id=room.id,
            session_id=body.session_id,
            user_id=user["sub"] if user else None,
            user_name=body.user_name or "Anonymous",
            joined_at=datetime.now(timezone.utc),
        )
        await daily_participant_sessions_controller.batch_upsert_sessions([session])

        active = await daily_participant_sessions_controller.get_active_by_meeting(
            meeting.id
        )
        await meetings_controller.update_meeting(meeting.id, num_clients=len(active))
        log.info(
            "Session created directly",
            session_id=body.session_id,
            num_clients=len(active),
        )

    # Trigger presence poll as reconciliation safety net
    if meeting.platform == "daily":
        poll_daily_room_presence_task.apply_async(args=[meeting_id], countdown=3)

    return JoinedResponse(status="ok")


class LeaveResponse(BaseModel):
    status: Literal["ok"]


@router.post(
    "/rooms/{room_name}/meetings/{meeting_id}/leave", response_model=LeaveResponse
)
async def meeting_leave(
    room_name: str,
    meeting_id: str,
    request: Request,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> LeaveResponse:
    """Trigger presence update when user leaves meeting.

    When session_id is provided in the body, closes the session directly
    for instant presence update. Falls back to polling when session_id
    is not available (e.g., sendBeacon without frame access).
    Called on tab close/navigation via sendBeacon().
    """
    # Parse session_id from body (sendBeacon may send text/plain or no body)
    session_id: str | None = None
    try:
        body_bytes = await request.body()
        if body_bytes:
            data = json.loads(body_bytes)
            raw = data.get("session_id")
            if isinstance(raw, str) and raw.strip():
                session_id = raw.strip()
    except Exception:
        pass

    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    meeting = await meetings_controller.get_by_id(meeting_id, room=room)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Close session directly when session_id provided
    session_closed = False
    if session_id and meeting.platform == "daily":
        existing = await daily_participant_sessions_controller.get_open_session(
            meeting.id, session_id
        )
        if existing:
            await daily_participant_sessions_controller.batch_close_sessions(
                [existing.id], left_at=datetime.now(timezone.utc)
            )
            active = await daily_participant_sessions_controller.get_active_by_meeting(
                meeting.id
            )
            await meetings_controller.update_meeting(
                meeting.id, num_clients=len(active)
            )
            session_closed = True

    # Only queue poll if we couldn't close directly — the poll runs before
    # Daily.co API removes the participant, which would undo our correct count
    if meeting.platform == "daily" and not session_closed:
        poll_daily_room_presence_task.apply_async(args=[meeting_id], countdown=3)

    return LeaveResponse(status="ok")
