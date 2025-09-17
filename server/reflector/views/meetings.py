from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.meetings import (
    MeetingConsent,
    meeting_consent_controller,
    meetings_controller,
)
from reflector.db.rooms import rooms_controller

router = APIRouter()


class MeetingConsentRequest(BaseModel):
    consent_given: bool


@router.post("/meetings/{meeting_id}/consent")
async def meeting_audio_consent(
    meeting_id: str,
    request: MeetingConsentRequest,
    user_request: Request,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    user_id = user["sub"] if user else None

    consent = MeetingConsent(
        meeting_id=meeting_id,
        user_id=user_id,
        consent_given=request.consent_given,
        consent_timestamp=datetime.now(timezone.utc),
    )

    updated_consent = await meeting_consent_controller.upsert(consent)

    return {"status": "success", "consent_id": updated_consent.id}


@router.patch("/meetings/{meeting_id}/deactivate")
async def meeting_deactivate(
    meeting_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user)],
):
    user_id = user["sub"] if user else None
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if not meeting.is_active:
        return {"status": "success", "meeting_id": meeting_id}

    # Only room owner or meeting creator can deactivate
    room = await rooms_controller.get_by_id(meeting.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if user_id != room.user_id and user_id != meeting.user_id:
        raise HTTPException(
            status_code=403, detail="Only the room owner can deactivate meetings"
        )

    await meetings_controller.update_meeting(meeting_id, is_active=False)

    return {"status": "success", "meeting_id": meeting_id}
