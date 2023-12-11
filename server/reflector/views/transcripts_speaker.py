"""
Reassign speakers in a transcript
=================================

"""
from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from reflector.db.transcripts import transcripts_controller

router = APIRouter()


class SpeakerAssignment(BaseModel):
    speaker: int
    timestamp_from: float
    timestamp_to: float


class SpeakerAssignmentStatus(BaseModel):
    status: str


class SpeakerMerge(BaseModel):
    speaker_from: int
    speaker_to: int


@router.patch("/transcripts/{transcript_id}/speaker/assign")
async def transcript_assign_speaker(
    transcript_id: str,
    assignment: SpeakerAssignment,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> SpeakerAssignmentStatus:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # reassign speakers from words in the transcript
    ts_from = assignment.timestamp_from
    ts_to = assignment.timestamp_to
    changed_topics = []
    for topic in transcript.topics:
        changed = False
        for word in topic.words:
            if ts_from <= word.start <= ts_to:
                word.speaker = assignment.speaker
                changed = True
        if changed:
            changed_topics.append(topic)

    # batch changes
    for topic in changed_topics:
        transcript.upsert_topic(topic)
    await transcripts_controller.update(
        transcript,
        {
            "topics": transcript.topics_dump(),
        },
    )

    return SpeakerAssignmentStatus(status="ok")


@router.patch("/transcripts/{transcript_id}/speaker/merge")
async def transcript_merge_speaker(
    transcript_id: str,
    merge: SpeakerMerge,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> SpeakerAssignmentStatus:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # ensure both speaker are not assigned to the 2 differents participants
    participant_from = next(
        (
            participant
            for participant in transcript.participants
            if participant.speaker == merge.speaker_from
        ),
        None,
    )
    participant_to = next(
        (
            participant
            for participant in transcript.participants
            if participant.speaker == merge.speaker_to
        ),
        None,
    )
    if participant_from and participant_to:
        raise HTTPException(
            status_code=400,
            detail="Both speakers are assigned to participants",
        )

    # reassign speakers from words in the transcript
    speaker_from = merge.speaker_from
    speaker_to = merge.speaker_to
    changed_topics = []
    for topic in transcript.topics:
        changed = False
        for word in topic.words:
            if word.speaker == speaker_from:
                word.speaker = speaker_to
                changed = True
        if changed:
            changed_topics.append(topic)

    # batch changes
    for topic in changed_topics:
        transcript.upsert_topic(topic)
    await transcripts_controller.update(
        transcript,
        {
            "topics": transcript.topics_dump(),
        },
    )

    return SpeakerAssignmentStatus(status="ok")
