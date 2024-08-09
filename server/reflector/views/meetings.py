from datetime import datetime
from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from reflector.db.meetings import meetings_controller

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
