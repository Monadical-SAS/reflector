import logging
from datetime import datetime, timezone
from typing import Annotated, Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel

import reflector.auth as auth
from reflector.dailyco_api import RecordingType
from reflector.db.meetings import (
    MeetingConsent,
    meeting_consent_controller,
    meetings_controller,
)
from reflector.db.rooms import rooms_controller
from reflector.utils.string import NonEmptyString
from reflector.video_platforms.factory import create_platform_client

logger = logging.getLogger(__name__)

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


class StartRecordingRequest(BaseModel):
    type: RecordingType
    instanceId: NonEmptyString


@router.post("/meetings/{meeting_id}/recordings/start")
async def start_recording(
    meeting_id: NonEmptyString, body: StartRecordingRequest
) -> dict[str, Any]:
    """Start cloud or raw-tracks recording via Daily.co REST API.

    Both cloud and raw-tracks are started via REST API to bypass enable_recording limitation.
    Uses different instanceIds for cloud vs raw-tracks.

    Note: No authentication required - anonymous users supported.
    """
    meeting = await meetings_controller.get_by_id(meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    try:
        client = create_platform_client("daily")
        result = await client.start_recording(
            room_name=meeting.room_name,
            recording_type=body.type,
            instance_id=body.instanceId,
        )

        logger.info(
            f"Started {body.type} recording via REST API",
            extra={
                "meeting_id": meeting_id,
                "room_name": meeting.room_name,
                "recording_type": body.type,
                "instance_id": body.instanceId,
            },
        )

        return {"status": "ok", "result": result}

    except Exception as e:
        logger.error(
            "Failed to start raw-tracks recording",
            extra={"meeting_id": meeting_id, "error": str(e)},
        )
        raise HTTPException(
            status_code=500, detail=f"Failed to start recording: {str(e)}"
        )
