from datetime import datetime

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from reflector.db.meetings import (
    MeetingConsent,
    meeting_consent_controller,
    meetings_controller,
)

router = APIRouter()


class MeetingConsentRequest(BaseModel):
    consent_given: bool
    user_identifier: str | None = None


@router.post("/meetings/{meeting_id}/consent")
async def meeting_audio_consent(
    meeting_id: str,
    request: MeetingConsentRequest,
    user_request: Request,
):
    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    
    # Store consent in meeting_consent table (create or update for authenticated users)
    consent = MeetingConsent(
        meeting_id=meeting_id,
        user_identifier=request.user_identifier,
        consent_given=request.consent_given,
        consent_timestamp=datetime.utcnow(),
        user_agent=user_request.headers.get("user-agent")
    )
    
    # Use create_or_update to handle consent overrides for authenticated users
    updated_consent = await meeting_consent_controller.create_or_update(consent)
    
    return {"status": "success", "consent_id": updated_consent.id}