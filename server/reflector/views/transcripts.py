from datetime import datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Annotated, Optional
from uuid import uuid4

import av
import reflector.auth as auth
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse
from fastapi_pagination import Page, paginate
from pydantic import BaseModel, Field
from reflector.db import database, transcripts
from reflector.logger import logger
from reflector.settings import settings
from starlette.concurrency import run_in_threadpool

from .rtc_offer import PipelineEvent, RtcOffer, rtc_offer_base

router = APIRouter()

# ==============================================================
# Models to move to a database, but required for the API to work
# ==============================================================


def generate_uuid4():
    return str(uuid4())


def generate_transcript_name():
    now = datetime.utcnow()
    return f"Transcript {now.strftime('%Y-%m-%d %H:%M:%S')}"


class TranscriptText(BaseModel):
    text: str


class TranscriptTopic(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    title: str
    summary: str
    transcript: str
    timestamp: float


class TranscriptFinalSummary(BaseModel):
    summary: str


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
    summary: str | None = None
    topics: list[TranscriptTopic] = []
    events: list[TranscriptEvent] = []

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

    def convert_audio_to_mp3(self):
        fn = self.audio_mp3_filename
        if fn.exists():
            return

        logger.info(f"Converting audio to mp3: {self.audio_filename}")
        inp = av.open(self.audio_filename.as_posix(), "r")

        # create temporary file for mp3
        with NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            out = av.open(tmp.name, "w")
            stream = out.add_stream("mp3")
            for frame in inp.decode(audio=0):
                frame.pts = None
                for packet in stream.encode(frame):
                    out.mux(packet)
            for packet in stream.encode(None):
                out.mux(packet)
            out.close()

            # move temporary file to final location
            import shutil

            shutil.move(tmp.name, fn.as_posix())

    def unlink(self):
        self.data_path.unlink(missing_ok=True)

    @property
    def data_path(self):
        return Path(settings.DATA_DIR) / self.id

    @property
    def audio_filename(self):
        return self.data_path / "audio.wav"

    @property
    def audio_mp3_filename(self):
        return self.data_path / "audio.mp3"


class TranscriptController:
    async def get_all(self, user_id: str | None = None) -> list[Transcript]:
        query = transcripts.select()
        if user_id is not None:
            query = query.where(transcripts.c.user_id == user_id)
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

    async def add(self, name: str, user_id: str | None = None):
        transcript = Transcript(name=name, user_id=user_id)
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
    created_at: datetime


class CreateTranscript(BaseModel):
    name: str


class UpdateTranscript(BaseModel):
    name: Optional[str] = Field(None)
    locked: Optional[bool] = Field(None)


class TranscriptEntryCreate(BaseModel):
    name: str


class DeletionStatus(BaseModel):
    status: str


@router.get("/transcripts", response_model=Page[GetTranscript])
async def transcripts_list(
    user: auth.UserInfo = Depends(auth.current_user),
):
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return paginate(await transcripts_controller.get_all(user_id=user["sub"]))


@router.post("/transcripts", response_model=GetTranscript)
async def transcripts_create(
    info: CreateTranscript,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    return await transcripts_controller.add(info.name, user_id=user_id)


# ==============================================================
# Single transcript
# ==============================================================


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


@router.get("/transcripts/{transcript_id}/audio")
async def transcript_get_audio(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not transcript.audio_filename.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    return FileResponse(transcript.audio_filename, media_type="audio/wav")


@router.get("/transcripts/{transcript_id}/audio/mp3")
async def transcript_get_audio_mp3(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    if not transcript.audio_filename.exists():
        raise HTTPException(status_code=404, detail="Audio not found")

    await run_in_threadpool(transcript.convert_audio_to_mp3)

    return FileResponse(transcript.audio_mp3_filename, media_type="audio/mp3")


@router.get("/transcripts/{transcript_id}/topics", response_model=list[TranscriptTopic])
async def transcript_get_topics(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id(transcript_id, user_id=user_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript.topics


@router.get("/transcripts/{transcript_id}/events")
async def transcript_get_websocket_events(transcript_id: str):
    pass


# ==============================================================
# Websocket Manager
# ==============================================================


class WebsocketManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, transcript_id: str, websocket: WebSocket):
        await websocket.accept()
        if transcript_id not in self.active_connections:
            self.active_connections[transcript_id] = []
        self.active_connections[transcript_id].append(websocket)

    def disconnect(self, transcript_id: str, websocket: WebSocket):
        if transcript_id not in self.active_connections:
            return
        self.active_connections[transcript_id].remove(websocket)
        if not self.active_connections[transcript_id]:
            del self.active_connections[transcript_id]

    async def send_json(self, transcript_id: str, message):
        if transcript_id not in self.active_connections:
            return
        for connection in self.active_connections[transcript_id][:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections[transcript_id].remove(connection)


ws_manager = WebsocketManager()


@router.websocket("/transcripts/{transcript_id}/events")
async def transcript_events_websocket(transcript_id: str, websocket: WebSocket):
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    await ws_manager.connect(transcript_id, websocket)

    # on first connection, send all events
    for event in transcript.events:
        await websocket.send_json(event.model_dump(mode="json"))

    # XXX if transcript is final (locked=True and status=ended)
    # XXX send a final event to the client and close the connection

    # endless loop to wait for new events
    try:
        while True:
            await websocket.receive()
    except (RuntimeError, WebSocketDisconnect):
        ws_manager.disconnect(transcript_id, websocket)


# ==============================================================
# Web RTC
# ==============================================================


async def handle_rtc_event(event: PipelineEvent, args, data):
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
        resp = transcript.add_event(event=event, data=TranscriptText(text=data.text))
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
            transcript=data.transcript.text,
            timestamp=data.timestamp,
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

    elif event == PipelineEvent.FINAL_SUMMARY:
        final_summary = TranscriptFinalSummary(summary=data.summary)
        resp = transcript.add_event(event=event, data=final_summary)
        await transcripts_controller.update(
            transcript,
            {
                "events": transcript.events_dump(),
                "summary": final_summary.summary,
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
    await ws_manager.send_json(transcript_id, resp.model_dump(mode="json"))


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
        audio_filename=transcript.audio_filename,
    )
