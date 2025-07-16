from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Optional

import reflector.auth as auth
from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import paginate
from jose import jwt
from pydantic import BaseModel, Field, field_serializer
from reflector.db.meetings import meetings_controller
from reflector.db.migrate_user import migrate_user
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import (
    SourceKind,
    TranscriptParticipant,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.processors.types import Word
from reflector.settings import settings
from reflector.zulip import (
    InvalidMessageError,
    get_zulip_message,
    send_message_to_zulip,
    update_zulip_message,
)

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


class GetTranscriptMinimal(BaseModel):
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
    reviewed: bool
    meeting_id: str | None

    @field_serializer("created_at")
    def serialize_datetime(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    source_kind: SourceKind
    room_id: str | None = None
    room_name: str | None = None
    audio_deleted: bool | None = None


class GetTranscript(GetTranscriptMinimal):
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
    reviewed: Optional[bool] = Field(None)
    audio_deleted: Optional[bool] = Field(None)


class DeletionStatus(BaseModel):
    status: str


@router.get("/transcripts", response_model=Page[GetTranscriptMinimal])
async def transcripts_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    source_kind: SourceKind | None = None,
    room_id: str | None = None,
    search_term: str | None = None,
):
    from reflector.db import database

    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    # for fief to jwt migration, migrate user if needed
    if user:
        await migrate_user(email=user["email"], user_id=user["sub"])

    return await paginate(
        database,
        await transcripts_controller.get_all(
            user_id=user_id,
            source_kind=SourceKind(source_kind) if source_kind else None,
            room_id=room_id,
            search_term=search_term,
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
        source_kind=SourceKind.LIVE,
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
    duration: float | None
    transcript: str
    segments: list[GetTranscriptSegmentTopic] = []

    @classmethod
    def from_transcript_topic(cls, topic: TranscriptTopic):
        if not topic.words:
            # In previous version, words were missing
            # Just output a segment with speaker 0
            text = topic.transcript
            duration = None
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
            duration = transcript.duration
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
            duration=duration,
        )


class GetTranscriptTopicWithWords(GetTranscriptTopic):
    words: list[Word] = []

    @classmethod
    def from_transcript_topic(cls, topic: TranscriptTopic):
        instance = super().from_transcript_topic(topic)
        if topic.words:
            instance.words = topic.words
        return instance


class SpeakerWords(BaseModel):
    speaker: int
    words: list[Word]


class GetTranscriptTopicWithWordsPerSpeaker(GetTranscriptTopic):
    words_per_speaker: list[SpeakerWords] = []

    @classmethod
    def from_transcript_topic(cls, topic: TranscriptTopic):
        instance = super().from_transcript_topic(topic)
        if topic.words:
            words_per_speakers = []
            # group words by speaker
            words = []
            for word in topic.words:
                if words and words[-1].speaker != word.speaker:
                    words_per_speakers.append(
                        SpeakerWords(
                            speaker=words[-1].speaker,
                            words=words,
                        )
                    )
                    words = []
                words.append(word)
            if words:
                words_per_speakers.append(
                    SpeakerWords(
                        speaker=words[-1].speaker,
                        words=words,
                    )
                )

            instance.words_per_speaker = words_per_speakers

        return instance


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
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
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
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if transcript.meeting_id:
        meeting = await meetings_controller.get_by_id(transcript.meeting_id)
        room = await rooms_controller.get_by_id(meeting.room_id)
        if room.is_shared:
            user_id = None

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


@router.get(
    "/transcripts/{transcript_id}/topics/with-words",
    response_model=list[GetTranscriptTopicWithWords],
)
async def transcript_get_topics_with_words(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    # convert to GetTranscriptTopicWithWords
    return [
        GetTranscriptTopicWithWords.from_transcript_topic(topic)
        for topic in transcript.topics
    ]


@router.get(
    "/transcripts/{transcript_id}/topics/{topic_id}/words-per-speaker",
    response_model=GetTranscriptTopicWithWordsPerSpeaker,
)
async def transcript_get_topics_with_words_per_speaker(
    transcript_id: str,
    topic_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    # get the topic from the transcript
    topic = next((t for t in transcript.topics if t.id == topic_id), None)
    if not topic:
        raise HTTPException(status_code=404, detail="Topic not found")

    # convert to GetTranscriptTopicWithWordsPerSpeaker
    return GetTranscriptTopicWithWordsPerSpeaker.from_transcript_topic(topic)


@router.post("/transcripts/{transcript_id}/zulip")
async def transcript_post_to_zulip(
    transcript_id: str,
    stream: str,
    topic: str,
    include_topics: bool,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    content = get_zulip_message(transcript, include_topics)

    message_updated = False
    if transcript.zulip_message_id:
        try:
            await update_zulip_message(
                transcript.zulip_message_id, stream, topic, content
            )
            message_updated = True
        except InvalidMessageError:
            pass

    if not message_updated:
        response = await send_message_to_zulip(stream, topic, content)
        await transcripts_controller.update(
            transcript, {"zulip_message_id": response["id"]}
        )
