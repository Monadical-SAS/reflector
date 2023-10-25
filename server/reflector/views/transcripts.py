import json
from datetime import datetime
from pathlib import Path
from typing import Annotated, Optional
from uuid import uuid4

import reflector.auth as auth
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi_pagination import Page, paginate
from pydantic import BaseModel, Field
from reflector.db import database, transcripts
from reflector.logger import logger
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.processors.types import Word as ProcessorWord
from reflector.settings import settings
from reflector.utils.audio_waveform import get_audio_waveform
from reflector.ws_manager import get_ws_manager
from starlette.concurrency import run_in_threadpool

from ._range_requests_response import range_requests_response
from .rtc_offer import PipelineEvent, RtcOffer, rtc_offer_base

router = APIRouter()
ws_manager = get_ws_manager()

# ==============================================================
# Models to move to a database, but required for the API to work
# ==============================================================


def generate_uuid4():
    return str(uuid4())


def generate_transcript_name():
    now = datetime.utcnow()
    return f"Transcript {now.strftime('%Y-%m-%d %H:%M:%S')}"


class AudioWaveform(BaseModel):
    data: list[float]


class TranscriptText(BaseModel):
    text: str
    translation: str | None


class TranscriptSegmentTopic(BaseModel):
    speaker: int
    text: str
    timestamp: float


class TranscriptTopic(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    title: str
    summary: str
    timestamp: float
    text: str | None = None
    words: list[ProcessorWord] = []


class TranscriptFinalShortSummary(BaseModel):
    short_summary: str


class TranscriptFinalLongSummary(BaseModel):
    long_summary: str


class TranscriptFinalTitle(BaseModel):
    title: str


class TranscriptEvent(BaseModel):
    event: str
    data: dict


class Transcript(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    user_id: str | None = None
    name: str = Field(default_factory=generate_transcript_name)
    status: str = "idle"
    locked: bool = False
    duration: float = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)
    title: str | None = None
    short_summary: str | None = None
    long_summary: str | None = None
    topics: list[TranscriptTopic] = []
    events: list[TranscriptEvent] = []
    source_language: str = "en"
    target_language: str = "en"

    def add_event(self, event: str, data: BaseModel) -> TranscriptEvent:
        ev = TranscriptEvent(event=event, data=data.model_dump())
        self.events.append(ev)
        return ev

    def upsert_topic(self, topic: TranscriptTopic):
        existing_topic = next((t for t in self.topics if t.id == topic.id), None)
        if existing_topic:
            existing_topic.update_from(topic)
        else:
            self.topics.append(topic)

    def events_dump(self, mode="json"):
        return [event.model_dump(mode=mode) for event in self.events]

    def topics_dump(self, mode="json"):
        return [topic.model_dump(mode=mode) for topic in self.topics]

    def convert_audio_to_waveform(self, segments_count=256):
        fn = self.audio_waveform_filename
        if fn.exists():
            return
        waveform = get_audio_waveform(
            path=self.audio_mp3_filename, segments_count=segments_count
        )
        try:
            with open(fn, "w") as fd:
                json.dump(waveform, fd)
        except Exception:
            # remove file if anything happen during the write
            fn.unlink(missing_ok=True)
            raise
        return waveform

    def unlink(self):
        self.data_path.unlink(missing_ok=True)

    @property
    def data_path(self):
        return Path(settings.DATA_DIR) / self.id

    @property
    def audio_mp3_filename(self):
        return self.data_path / "audio.mp3"

    @property
    def audio_waveform_filename(self):
        return self.data_path / "audio.json"

    @property
    def audio_waveform(self):
        try:
            with open(self.audio_waveform_filename) as fd:
                data = json.load(fd)
        except json.JSONDecodeError:
            # unlink file if it's corrupted
            self.audio_waveform_filename.unlink(missing_ok=True)
            return None

        return AudioWaveform(data=data)


class TranscriptController:
    async def get_all(
        self,
        user_id: str | None = None,
        order_by: str | None = None,
        filter_empty: bool | None = False,
        filter_recording: bool | None = False,
    ) -> list[Transcript]:
        query = transcripts.select().where(transcripts.c.user_id == user_id)

        if order_by is not None:
            field = getattr(transcripts.c, order_by[1:])
            if order_by.startswith("-"):
                field = field.desc()
            query = query.order_by(field)

        if filter_empty:
            query = query.filter(transcripts.c.status != "idle")

        if filter_recording:
            query = query.filter(transcripts.c.status != "recording")

        results = await database.fetch_all(query)
        return results

    async def get_by_id(self, transcript_id: str, **kwargs) -> Transcript | None:
        query = transcripts.select().where(transcripts.c.id == transcript_id)
        if "user_id" in kwargs:
            query = query.where(transcripts.c.user_id == kwargs["user_id"])
        result = await database.fetch_one(query)
        if not result:
            return None
        return Transcript(**result)

    async def add(
        self,
        name: str,
        source_language: str = "en",
        target_language: str = "en",
        user_id: str | None = None,
    ):
        transcript = Transcript(
            name=name,
            source_language=source_language,
            target_language=target_language,
            user_id=user_id,
        )
        query = transcripts.insert().values(**transcript.model_dump())
        await database.execute(query)
        return transcript

    async def update(self, transcript: Transcript, values: dict):
        query = (
            transcripts.update()
            .where(transcripts.c.id == transcript.id)
            .values(**values)
        )
        await database.execute(query)
        for key, value in values.items():
            setattr(transcript, key, value)

    async def remove_by_id(
        self, transcript_id: str, user_id: str | None = None
    ) -> None:
        transcript = await self.get_by_id(transcript_id, user_id=user_id)
        if not transcript:
            return
        if user_id is not None and transcript.user_id != user_id:
            return
        transcript.unlink()
        query = transcripts.delete().where(transcripts.c.id == transcript_id)
        await database.execute(query)


transcripts_controller = TranscriptController()


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
    values = {"events": []}
    if info.name is not None:
        values["name"] = info.name
    if info.locked is not None:
        values["locked"] = info.locked
    if info.long_summary is not None:
        values["long_summary"] = info.long_summary
        for transcript_event in transcript.events:
            if transcript_event["event"] == PipelineEvent.FINAL_LONG_SUMMARY:
                transcript_event["long_summary"] = info.long_summary
                break
        values["events"].extend(transcript.events)
    if info.short_summary is not None:
        values["short_summary"] = info.short_summary
        for transcript_event in transcript.events:
            if transcript_event["event"] == PipelineEvent.FINAL_SHORT_SUMMARY:
                transcript_event["short_summary"] = info.short_summary
                break
        values["events"].extend(transcript.events)
    if info.title is not None:
        values["title"] = info.title
        for transcript_event in transcript.events:
            if transcript_event["event"] == PipelineEvent.FINAL_TITLE:
                transcript_event["title"] = info.title
                break
        values["events"].extend(transcript.events)
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
):
    user_id = user["sub"] if user else None
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


@router.get("/transcripts/{transcript_id}/events")
async def transcript_get_websocket_events(transcript_id: str):
    pass


# ==============================================================
# Websocket
# ==============================================================


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
    await ws_manager.add_user_to_room(room_id, websocket)

    try:
        # on first connection, send all events only to the current user
        for event in transcript.events:
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


async def handle_rtc_event(event: PipelineEvent, args, data):
    try:
        return await handle_rtc_event_once(event, args, data)
    except Exception:
        logger.exception("Error handling RTC event")


async def handle_rtc_event_once(event: PipelineEvent, args, data):
    # OFC the current implementation is not good,
    # but it's just a POC before persistence. It won't query the
    # transcript from the database for each event.
    # print(f"Event: {event}", args, data)
    transcript_id = args
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        return

    # event send to websocket clients may not be the same as the event
    # received from the pipeline. For example, the pipeline will send
    # a TRANSCRIPT event with all words, but this is not what we want
    # to send to the websocket client.

    # FIXME don't do copy
    if event == PipelineEvent.TRANSCRIPT:
        resp = transcript.add_event(
            event=event,
            data=TranscriptText(text=data.text, translation=data.translation),
        )
        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
            },
        )

    elif event == PipelineEvent.TOPIC:
        topic = TranscriptTopic(
            title=data.title,
            summary=data.summary,
            timestamp=data.timestamp,
            text=data.transcript.text,
            words=data.transcript.words,
        )
        resp = transcript.add_event(event=event, data=topic)
        transcript.upsert_topic(topic)

        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
                "topics": transcript.topics_dump(),
            },
        )

    elif event == PipelineEvent.FINAL_TITLE:
        final_title = TranscriptFinalTitle(title=data.title)
        resp = transcript.add_event(event=event, data=final_title)
        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
                "title": final_title.title,
            },
        )

    elif event == PipelineEvent.FINAL_LONG_SUMMARY:
        final_long_summary = TranscriptFinalLongSummary(long_summary=data.long_summary)
        resp = transcript.add_event(event=event, data=final_long_summary)
        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
                "long_summary": final_long_summary.long_summary,
            },
        )

    elif event == PipelineEvent.FINAL_SHORT_SUMMARY:
        final_short_summary = TranscriptFinalShortSummary(
            short_summary=data.short_summary
        )
        resp = transcript.add_event(event=event, data=final_short_summary)
        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
                "short_summary": final_short_summary.short_summary,
            },
        )

    elif event == PipelineEvent.STATUS:
        resp = transcript.add_event(event=event, data=data)
        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
                "status": data.value,
            },
        )

    else:
        logger.warning(f"Unknown event: {event}")
        return

    # transmit to websocket clients
    room_id = f"ts:{transcript_id}"
    await ws_manager.send_json(room_id, resp.model_dump(mode="json"))


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

    # FIXME do not allow multiple recording at the same time
    return await rtc_offer_base(
        params,
        request,
        event_callback=handle_rtc_event,
        event_callback_args=transcript_id,
        audio_filename=transcript.audio_mp3_filename,
        source_language=transcript.source_language,
        target_language=transcript.target_language,
    )
