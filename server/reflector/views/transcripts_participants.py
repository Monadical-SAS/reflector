"""
Transcript participants API endpoints
=====================================

"""
from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from reflector.db.transcripts import TranscriptParticipant, transcripts_controller
from reflector.views.types import DeletionStatus

router = APIRouter()


class Participant(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    speaker: int | None
    name: str


class CreateParticipant(BaseModel):
    speaker: Optional[int] = Field(None)
    name: str


class UpdateParticipant(BaseModel):
    speaker: Optional[int] = Field(None)
    name: Optional[str] = Field(None)


@router.get("/transcripts/{transcript_id}/participants")
async def transcript_get_participants(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> list[Participant]:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    return [
        Participant.model_validate(participant)
        for participant in transcript.participants
    ]


@router.post("/transcripts/{transcript_id}/participants")
async def transcript_add_participant(
    transcript_id: str,
    participant: CreateParticipant,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> Participant:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    # ensure the speaker is unique
    for p in transcript.participants:
        if p.speaker == participant.speaker:
            raise HTTPException(
                status_code=400,
                detail="Speaker already assigned",
            )

    obj = await transcripts_controller.upsert_participant(
        transcript, TranscriptParticipant(**participant.dict())
    )
    return Participant.model_validate(obj)


@router.get("/transcripts/{transcript_id}/participants/{participant_id}")
async def transcript_get_participant(
    transcript_id: str,
    participant_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> Participant:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    for p in transcript.participants:
        if p.id == participant_id:
            return Participant.model_validate(p)

    raise HTTPException(status_code=404, detail="Participant not found")


@router.patch("/transcripts/{transcript_id}/participants/{participant_id}")
async def transcript_update_participant(
    transcript_id: str,
    participant_id: str,
    participant: UpdateParticipant,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> Participant:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    # ensure the speaker is unique
    for p in transcript.participants:
        if p.speaker == participant.speaker and p.id != participant_id:
            raise HTTPException(
                status_code=400,
                detail="Speaker already assigned",
            )

    # find the participant
    obj = None
    for p in transcript.participants:
        if p.id == participant_id:
            obj = p
            break

    if not obj:
        raise HTTPException(status_code=404, detail="Participant not found")

    # update participant but just the fields that are set
    fields = participant.dict(exclude_unset=True)
    obj = obj.copy(update=fields)

    await transcripts_controller.upsert_participant(transcript, obj)
    return Participant.model_validate(obj)


@router.delete("/transcripts/{transcript_id}/participants/{participant_id}")
async def transcript_delete_participant(
    transcript_id: str,
    participant_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> DeletionStatus:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    await transcripts_controller.delete_participant(transcript, participant_id)
    return DeletionStatus(status="ok")
