from datetime import datetime, timedelta
from typing import Annotated, Literal, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from jose import jwt
from pydantic import BaseModel, Field
from reflector.db.transcripts import (
    TranscriptParticipant,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.settings import settings

router = APIRouter()

ALGORITHM = "HS256"
DOWNLOAD_EXPIRE_MINUTES = 60


def create_access_token(data: dict, expires_delta: timedelta):
    to_encode = data.copy()
    expire = datetime.utcnow() + expires_delta
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# ==============================================================
# Transcripts list
# ==============================================================


class GetTranscript(BaseModel):
    id: str
    user_id: str | None
    name: str
    status: str
    locked: bool
    duration: float
    title: str | None
    short_summary: str | None
    long_summary: str | None
    created_at: datetime
    share_mode: str = Field("private")
    source_language: str | None
    target_language: str | None
    participants: list[TranscriptParticipant] | None


class CreateTranscript(BaseModel):
    name: str
    source_language: str = Field("en")
    target_language: str = Field("en")


class UpdateTranscript(BaseModel):
    name: Optional[str] = Field(None)
    locked: Optional[bool] = Field(None)
    title: Optional[str] = Field(None)
    short_summary: Optional[str] = Field(None)
    long_summary: Optional[str] = Field(None)
    share_mode: Optional[Literal["public", "semi-private", "private"]] = Field(None)
    participants: Optional[list[TranscriptParticipant]] = Field(None)


class DeletionStatus(BaseModel):
    status: str


@router.get("/transcripts", response_model=Page[GetTranscript])
async def transcripts_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    from reflector.db import database

    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None
    return await paginate(
        database,
        await transcripts_controller.get_all(
            user_id=user_id,
            order_by="-created_at",
            return_query=True,
        ),
    )


@router.post("/transcripts", response_model=GetTranscript)
async def transcripts_create(
    info: CreateTranscript,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    return await transcripts_controller.add(
        info.name,
        source_language=info.source_language,
        target_language=info.target_language,
        user_id=user_id,
    )


# ==============================================================
# Single transcript
# ==============================================================


class GetTranscriptSegmentTopic(BaseModel):
    text: str
    start: float
    speaker: int


class GetTranscriptTopic(BaseModel):
    id: str
    title: str
    summary: str
    timestamp: float
    transcript: str
    segments: list[GetTranscriptSegmentTopic] = []

    @classmethod
    def from_transcript_topic(cls, topic: TranscriptTopic):
        if not topic.words:
            # In previous version, words were missing
            # Just output a segment with speaker 0
            text = topic.transcript
            segments = [
                GetTranscriptSegmentTopic(
                    text=topic.transcript,
                    start=topic.timestamp,
                    speaker=0,
                )
            ]
        else:
            # New versions include words
            transcript = ProcessorTranscript(words=topic.words)
            text = transcript.text
            segments = [
                GetTranscriptSegmentTopic(
                    text=segment.text,
                    start=segment.start,
                    speaker=segment.speaker,
                )
                for segment in transcript.as_segments()
            ]
        return cls(
            id=topic.id,
            title=topic.title,
            summary=topic.summary,
            timestamp=topic.timestamp,
            transcript=text,
            segments=segments,
        )


@router.get("/transcripts/{transcript_id}", response_model=GetTranscript)
async def transcript_get(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    return await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )


@router.patch("/transcripts/{transcript_id}", response_model=GetTranscript)
async def transcript_update(
    transcript_id: str,
    info: UpdateTranscript,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    values = info.dict(exclude_unset=True)
    await transcripts_controller.update(transcript, values)
    return transcript


@router.delete("/transcripts/{transcript_id}", response_model=DeletionStatus)
async def transcript_delete(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    await transcripts_controller.remove_by_id(transcript.id, user_id=user_id)
    return DeletionStatus(status="ok")


@router.get(
    "/transcripts/{transcript_id}/topics",
    response_model=list[GetTranscriptTopic],
)
async def transcript_get_topics(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    # convert to GetTranscriptTopic
    return [
        GetTranscriptTopic.from_transcript_topic(topic) for topic in transcript.topics
    ]
