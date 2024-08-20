from datetime import datetime, timedelta, timezone
from http.client import HTTPException
from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from pydantic import BaseModel
from reflector.db import database
from reflector.db.meetings import meetings_controller
from reflector.db.rooms import rooms_controller
from reflector.settings import settings
from reflector.views.meetings import GetMeeting
from reflector.whereby import create_meeting

router = APIRouter()


class Room(BaseModel):
    id: str
    name: str
    user_id: str
    created_at: datetime


class CreateRoom(BaseModel):
    name: str


class DeletionStatus(BaseModel):
    status: str


@router.get("/rooms", response_model=Page[Room])
async def rooms_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[Room]:
    user_id = user["sub"] if user else None

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
    )


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


@router.post("/rooms/{room_name}/meeting", response_model=GetMeeting)
async def rooms_create_meeting(
    room_name: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    room = await rooms_controller.get_by_name(room_name)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    meeting = await meetings_controller.get_latest(room_id=room.id)
    if meeting is None:
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(hours=1)
        meeting = await create_meeting("", start_date=start_date, end_date=end_date)

        meeting = await meetings_controller.create(
            id=meeting["meetingId"],
            room_name=meeting["roomName"],
            room_url=meeting["roomUrl"],
            host_room_url=meeting["hostRoomUrl"],
            viewer_room_url=meeting["viewerRoomUrl"],
            start_date=datetime.fromisoformat(meeting["startDate"]),
            end_date=datetime.fromisoformat(meeting["endDate"]),
            user_id=user_id,
            room_id=room.id,
        )

    return meeting
