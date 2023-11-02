from datetime import datetime, timedelta
from typing import Annotated, Optional

import reflector.auth as auth
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
    status,
)
from fastapi_pagination import Page, paginate
from jose import jwt
from pydantic import BaseModel, Field
from reflector.db.transcripts import (
    AudioWaveform,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.settings import settings
from reflector.ws_manager import get_ws_manager
from starlette.concurrency import run_in_threadpool

from ._range_requests_response import range_requests_response
from .rtc_offer import RtcOffer, rtc_offer_base

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
    name: str
    status: str
    locked: bool
    duration: int
    title: str | None
    short_summary: str | None
    long_summary: str | None
    created_at: datetime
    source_language: str | None
    target_language: str | None


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


class DeletionStatus(BaseModel):
    status: str


@router.get("/transcripts", response_model=Page[GetTranscript])
async def transcripts_list(
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    if not user and not settings.PUBLIC_MODE:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user_id = user["sub"] if user else None
    return paginate(
        await transcripts_controller.get_all(user_id=user_id, order_by="-created_at")
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
    text: str
    segments: list[GetTranscriptSegmentTopic] = []

    @classmethod
    def from_transcript_topic(cls, topic: TranscriptTopic):
        if not topic.words:
            # In previous version, words were missing
            # Just output a segment with speaker 0
            text = topic.text
            segments = [
                GetTranscriptSegmentTopic(
                    text=topic.text,
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
            text=text,
            segments=segments,
        )


@router.get("/transcripts/{transcript_id}", response_model=GetTranscript)
async def transcript_get(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


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
    values = {}
    if info.name is not None:
        values["name"] = info.name
    if info.locked is not None:
        values["locked"] = info.locked
    if info.long_summary is not None:
        values["long_summary"] = info.long_summary
    if info.short_summary is not None:
        values["short_summary"] = info.short_summary
    if info.title is not None:
        values["title"] = info.title
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


@router.get("/transcripts/{transcript_id}/audio/mp3")
async def transcript_get_audio_mp3(
    request: Request,
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
    token: str | None = None,
):
    user_id = user["sub"] if user else None
    if not user_id and token:
        unauthorized_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_id: str = payload.get("sub")
        except jwt.JWTError:
            raise unauthorized_exception

    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not transcript.audio_mp3_filename.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    truncated_id = str(transcript.id).split("-")[0]
    filename = f"recording_{truncated_id}.mp3"

    return range_requests_response(
        request,
        transcript.audio_mp3_filename,
        content_type="audio/mpeg",
        content_disposition=f"attachment; filename={filename}",
    )


@router.get("/transcripts/{transcript_id}/audio/waveform")
async def transcript_get_audio_waveform(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
) -> AudioWaveform:
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not transcript.audio_mp3_filename.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    await run_in_threadpool(transcript.convert_audio_to_waveform)

    return transcript.audio_waveform


@router.get(
    "/transcripts/{transcript_id}/topics",
    response_model=list[GetTranscriptTopic],
)
async def transcript_get_topics(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # convert to GetTranscriptTopic
    return [
        GetTranscriptTopic.from_transcript_topic(topic) for topic in transcript.topics
    ]


# ==============================================================
# Websocket
# ==============================================================


@router.get("/transcripts/{transcript_id}/events")
async def transcript_get_websocket_events(transcript_id: str):
    pass


@router.websocket("/transcripts/{transcript_id}/events")
async def transcript_events_websocket(
    transcript_id: str,
    websocket: WebSocket,
    # user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    # user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # connect to websocket manager
    # use ts:transcript_id as room id
    room_id = f"ts:{transcript_id}"
    ws_manager = get_ws_manager()
    await ws_manager.add_user_to_room(room_id, websocket)

    try:
        # on first connection, send all events only to the current user
        for event in transcript.events:
            # for now, do not send TRANSCRIPT or STATUS options - theses are live event
            # not necessary to be sent to the client; but keep the rest
            name = event.event
            if name in ("TRANSCRIPT", "STATUS"):
                continue
            await websocket.send_json(event.model_dump(mode="json"))

        # XXX if transcript is final (locked=True and status=ended)
        # XXX send a final event to the client and close the connection

        # endless loop to wait for new events
        # we do not have command system now,
        while True:
            await websocket.receive()
    except (RuntimeError, WebSocketDisconnect):
        await ws_manager.remove_user_from_room(room_id, websocket)


# ==============================================================
# Web RTC
# ==============================================================


@router.post("/transcripts/{transcript_id}/record/webrtc")
async def transcript_record_webrtc(
    transcript_id: str,
    params: RtcOffer,
    request: Request,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if transcript.locked:
        raise HTTPException(status_code=400, detail="Transcript is locked")

    # create a pipeline runner
    from reflector.pipelines.main_live_pipeline import PipelineMainLive

    pipeline_runner = PipelineMainLive(transcript_id=transcript_id)

    # FIXME do not allow multiple recording at the same time
    return await rtc_offer_base(
        params,
        request,
        pipeline_runner=pipeline_runner,
    )
