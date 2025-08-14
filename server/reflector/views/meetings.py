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
