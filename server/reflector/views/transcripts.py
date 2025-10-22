from datetime import datetime, timedelta, timezone
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_pagination import Page
from fastapi_pagination.ext.databases import apaginate
from jose import jwt
from pydantic import BaseModel, Discriminator, Field, constr, field_serializer

import reflector.auth as auth
from reflector.db import get_database
from reflector.db.search import (
    DEFAULT_SEARCH_LIMIT,
    SearchLimit,
    SearchLimitBase,
    SearchOffset,
    SearchOffsetBase,
    SearchParameters,
    SearchQuery,
    SearchResult,
    SearchTotal,
    search_controller,
    search_query_adapter,
)
from reflector.db.transcripts import (
    SourceKind,
    TranscriptParticipant,
    TranscriptStatus,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.processors.types import Word
from reflector.schemas.transcript_formats import TranscriptFormat, TranscriptSegment
from reflector.settings import settings
from reflector.utils.transcript_formats import (
    topics_to_webvtt_named,
    transcript_to_json_segments,
    transcript_to_text,
    transcript_to_text_timestamped,
)
from reflector.ws_manager import get_ws_manager
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
    expire = datetime.now(timezone.utc) + expires_delta
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
    status: TranscriptStatus
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

    @field_serializer("created_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    source_kind: SourceKind
    room_id: str | None = None
    room_name: str | None = None
    audio_deleted: bool | None = None


class GetTranscriptWithParticipants(GetTranscriptMinimal):
    participants: list[TranscriptParticipant] | None


class GetTranscriptWithText(GetTranscriptWithParticipants):
    """
    Transcript response with plain text format.

    Format: Speaker names followed by their dialogue, one line per segment.
    Example:
        John Smith: Hello everyone
        Jane Doe: Hi there
    """

    transcript_format: Literal["text"] = "text"
    transcript: str


class GetTranscriptWithTextTimestamped(GetTranscriptWithParticipants):
    """
    Transcript response with timestamped text format.

    Format: [MM:SS] timestamp prefix before each speaker and dialogue.
    Example:
        [00:00] John Smith: Hello everyone
        [00:05] Jane Doe: Hi there
    """

    transcript_format: Literal["text-timestamped"] = "text-timestamped"
    transcript: str


class GetTranscriptWithWebVTTNamed(GetTranscriptWithParticipants):
    """
    Transcript response in WebVTT subtitle format with participant names.

    Format: Standard WebVTT with voice tags using participant names.
    Example:
        WEBVTT

        00:00:00.000 --> 00:00:05.000
        <v John Smith>Hello everyone
    """

    transcript_format: Literal["webvtt-named"] = "webvtt-named"
    transcript: str


class GetTranscriptWithJSON(GetTranscriptWithParticipants):
    """
    Transcript response as structured JSON segments.

    Format: Array of segment objects with speaker info, text, and timing.
    Example:
        [
            {
                "speaker": 0,
                "speaker_name": "John Smith",
                "text": "Hello everyone",
                "start": 0.0,
                "end": 5.0
            }
        ]
    """

    transcript_format: Literal["json"] = "json"
    transcript: list[TranscriptSegment]


GetTranscript = Annotated[
    GetTranscriptWithText
    | GetTranscriptWithTextTimestamped
    | GetTranscriptWithWebVTTNamed
    | GetTranscriptWithJSON,
    Discriminator("transcript_format"),
]


class CreateTranscript(BaseModel):
    name: str
    source_language: str = Field("en")
    target_language: str = Field("en")
    source_kind: SourceKind | None = None


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


SearchQueryParamBase = constr(min_length=0, strip_whitespace=True)
SearchQueryParam = Annotated[
    SearchQueryParamBase, Query(description="Search query text")
]


# http and api standards accept "q="; we would like to handle it as the absence of query, not as "empty string query"
def parse_search_query_param(q: SearchQueryParam) -> SearchQuery | None:
    if q == "":
        return None
    return search_query_adapter.validate_python(q)


SearchLimitParam = Annotated[SearchLimitBase, Query(description="Results per page")]
SearchOffsetParam = Annotated[
    SearchOffsetBase, Query(description="Number of results to skip")
]


class SearchResponse(BaseModel):
    results: list[SearchResult]
    total: SearchTotal
    query: SearchQuery | None = None
    limit: SearchLimit
    offset: SearchOffset


@router.get("/transcripts", response_model=Page[GetTranscriptMinimal])
async def transcripts_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    source_kind: SourceKind | None = None,
    room_id: str | None = None,
    search_term: str | None = None,
):
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    return await apaginate(
        get_database(),
        await transcripts_controller.get_all(
            user_id=user_id,
            source_kind=SourceKind(source_kind) if source_kind else None,
            room_id=room_id,
            search_term=search_term,
            order_by="-created_at",
            return_query=True,
        ),
    )


@router.get("/transcripts/search", response_model=SearchResponse)
async def transcripts_search(
    q: SearchQueryParam,
    limit: SearchLimitParam = DEFAULT_SEARCH_LIMIT,
    offset: SearchOffsetParam = 0,
    room_id: Optional[str] = None,
    source_kind: Optional[SourceKind] = None,
    user: Annotated[
        Optional[auth.UserInfo], Depends(auth.current_user_optional)
    ] = None,
):
    """
    Full-text search across transcript titles and content.
    """
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None

    search_params = SearchParameters(
        query_text=parse_search_query_param(q),
        limit=limit,
        offset=offset,
        user_id=user_id,
        room_id=room_id,
        source_kind=source_kind,
    )

    results, total = await search_controller.search_transcripts(search_params)

    return SearchResponse(
        results=results,
        total=total,
        query=search_params.query_text,
        limit=search_params.limit,
        offset=search_params.offset,
    )


@router.post("/transcripts", response_model=GetTranscriptWithParticipants)
async def transcripts_create(
    info: CreateTranscript,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.add(
        info.name,
        source_kind=info.source_kind or SourceKind.LIVE,
        source_language=info.source_language,
        target_language=info.target_language,
        user_id=user_id,
    )

    if user_id:
        await get_ws_manager().send_json(
            room_id=f"user:{user_id}",
            message={"event": "TRANSCRIPT_CREATED", "data": {"id": transcript.id}},
        )

    return transcript


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
    transcript_format: TranscriptFormat = "text",
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    base_data = {
        "id": transcript.id,
        "user_id": transcript.user_id,
        "name": transcript.name,
        "status": transcript.status,
        "locked": transcript.locked,
        "duration": transcript.duration,
        "title": transcript.title,
        "short_summary": transcript.short_summary,
        "long_summary": transcript.long_summary,
        "created_at": transcript.created_at,
        "share_mode": transcript.share_mode,
        "source_language": transcript.source_language,
        "target_language": transcript.target_language,
        "reviewed": transcript.reviewed,
        "meeting_id": transcript.meeting_id,
        "source_kind": transcript.source_kind,
        "room_id": transcript.room_id,
        "audio_deleted": transcript.audio_deleted,
        "participants": transcript.participants,
    }

    if transcript_format == "text":
        return GetTranscriptWithText(
            **base_data,
            transcript_format="text",
            transcript=transcript_to_text(transcript.topics, transcript.participants),
        )
    elif transcript_format == "text-timestamped":
        return GetTranscriptWithTextTimestamped(
            **base_data,
            transcript_format="text-timestamped",
            transcript=transcript_to_text_timestamped(
                transcript.topics, transcript.participants
            ),
        )
    elif transcript_format == "webvtt-named":
        return GetTranscriptWithWebVTTNamed(
            **base_data,
            transcript_format="webvtt-named",
            transcript=topics_to_webvtt_named(
                transcript.topics, transcript.participants
            ),
        )
    elif transcript_format == "json":
        return GetTranscriptWithJSON(
            **base_data,
            transcript_format="json",
            transcript=transcript_to_json_segments(
                transcript.topics, transcript.participants
            ),
        )


@router.patch(
    "/transcripts/{transcript_id}", response_model=GetTranscriptWithParticipants
)
async def transcript_update(
    transcript_id: str,
    info: UpdateTranscript,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcripts_controller.user_can_mutate(transcript, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    values = info.dict(exclude_unset=True)
    updated_transcript = await transcripts_controller.update(transcript, values)
    return updated_transcript


@router.delete("/transcripts/{transcript_id}", response_model=DeletionStatus)
async def transcript_delete(
    transcript_id: str,
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if not transcripts_controller.user_can_mutate(transcript, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    await transcripts_controller.remove_by_id(transcript.id, user_id=user_id)
    await get_ws_manager().send_json(
        room_id=f"user:{user_id}",
        message={"event": "TRANSCRIPT_DELETED", "data": {"id": transcript.id}},
    )
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
    user: Annotated[auth.UserInfo, Depends(auth.current_user)],
):
    user_id = user["sub"]
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if not transcripts_controller.user_can_mutate(transcript, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
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
