from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from reflector.db.meetings import meetings_controller
from reflector.whereby import create_meeting

router = APIRouter()


class GetMeeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    viewer_room_url: str
    start_date: datetime
    end_date: datetime


@router.get("/meetings/{meeting_id}", response_model=GetMeeting)
async def meeting_get(
    meeting_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    return await meetings_controller.get_by_id_for_http(meeting_id, user_id=user_id)


@router.post("/meetings/", response_model=GetMeeting)
async def meeting_create(
    room_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    meeting = await meetings_controller.get_latest(room_id)
    if meeting is None:
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(minutes=1)
        meeting = await create_meeting("", start_date=start_date, end_date=end_date)

        meeting = await meetings_controller.add(
            id=meeting["meetingId"],
            room_name=meeting["roomName"],
            room_url=meeting["roomUrl"],
            host_room_url=meeting["hostRoomUrl"],
            viewer_room_url=meeting["viewerRoomUrl"],
            start_date=datetime.fromisoformat(meeting["startDate"]),
            end_date=datetime.fromisoformat(meeting["endDate"]),
            user_id=user_id,
            room_id=room_id,
        )

    return await meetings_controller.get_by_id_for_http(meeting.id, user_id=user_id)
