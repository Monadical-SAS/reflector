from fastapi import APIRouter, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from uuid import UUID, uuid4
from datetime import datetime
from fastapi_pagination import Page, paginate
from reflector.logger import logger
from .rtc_offer import rtc_offer_base, RtcOffer, PipelineEvent
import asyncio
from typing import Optional


router = APIRouter()

# ==============================================================
# Models to move to a database, but required for the API to work
# ==============================================================


def generate_transcript_name():
    now = datetime.utcnow()
    return f"Transcript {now.strftime('%Y-%m-%d %H:%M:%S')}"


class TranscriptText(BaseModel):
    text: str


class TranscriptTopic(BaseModel):
    id: UUID = Field(default_factory=uuid4)
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
    id: UUID = Field(default_factory=uuid4)
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


class TranscriptController:
    transcripts: list[Transcript] = []

    def get_all(self) -> list[Transcript]:
        return self.transcripts

    def get_by_id(self, transcript_id: UUID) -> Transcript | None:
        return next((t for t in self.transcripts if t.id == transcript_id), None)

    def add(self, transcript: Transcript):
        self.transcripts.append(transcript)

    def remove(self, transcript: Transcript):
        self.transcripts.remove(transcript)


transcripts_controller = TranscriptController()


# ==============================================================
# Transcripts list
# ==============================================================


class GetTranscript(BaseModel):
    id: UUID
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
async def transcripts_list():
    return paginate(transcripts_controller.get_all())


@router.post("/transcripts", response_model=GetTranscript)
async def transcripts_create(info: CreateTranscript):
    transcript = Transcript()
    transcript.name = info.name
    transcripts_controller.add(transcript)
    return transcript


# ==============================================================
# Single transcript
# ==============================================================


@router.get("/transcripts/{transcript_id}", response_model=GetTranscript)
async def transcript_get(transcript_id: UUID):
    transcript = transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript


@router.patch("/transcripts/{transcript_id}", response_model=GetTranscript)
async def transcript_update(transcript_id: UUID, info: UpdateTranscript):
    transcript = transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    if info.name is not None:
        transcript.name = info.name
    if info.locked is not None:
        transcript.locked = info.locked
    return transcript


@router.delete("/transcripts/{transcript_id}", response_model=DeletionStatus)
async def transcript_delete(transcript_id: UUID):
    transcript = transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    transcripts_controller.remove(transcript)
    return DeletionStatus(status="ok")


@router.get("/transcripts/{transcript_id}/audio")
async def transcript_get_audio(transcript_id: UUID):
    transcript = transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # TODO: Implement audio generation
    return HTTPException(status_code=500, detail="Not implemented")


@router.get("/transcripts/{transcript_id}/topics", response_model=list[TranscriptTopic])
async def transcript_get_topics(transcript_id: UUID):
    transcript = transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")
    return transcript.topics


@router.get("/transcripts/{transcript_id}/events")
async def transcript_get_websocket_events(transcript_id: UUID):
    pass


# ==============================================================
# Websocket Manager
# ==============================================================


class WebsocketManager:
    def __init__(self):
        self.active_connections = {}

    async def connect(self, transcript_id: UUID, websocket: WebSocket):
        await websocket.accept()
        if transcript_id not in self.active_connections:
            self.active_connections[transcript_id] = []
        self.active_connections[transcript_id].append(websocket)

    def disconnect(self, transcript_id: UUID, websocket: WebSocket):
        if transcript_id not in self.active_connections:
            return
        self.active_connections[transcript_id].remove(websocket)
        if not self.active_connections[transcript_id]:
            del self.active_connections[transcript_id]

    async def send_json(self, transcript_id: UUID, message):
        if transcript_id not in self.active_connections:
            return
        for connection in self.active_connections[transcript_id][:]:
            try:
                await connection.send_json(message)
            except Exception:
                self.active_connections[transcript_id].remove(connection)


ws_manager = WebsocketManager()


@router.websocket("/transcripts/{transcript_id}/events")
async def transcript_events_websocket(transcript_id: UUID, websocket: WebSocket):
    transcript = transcripts_controller.get_by_id(transcript_id)
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
            await asyncio.sleep(42)
    except WebSocketDisconnect:
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
    transcript = transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        return

    # event send to websocket clients may not be the same as the event
    # received from the pipeline. For example, the pipeline will send
    # a TRANSCRIPT event with all words, but this is not what we want
    # to send to the websocket client.

    # FIXME don't do copy
    if event == PipelineEvent.TRANSCRIPT:
        resp = transcript.add_event(event=event, data=TranscriptText(text=data.text))

    elif event == PipelineEvent.TOPIC:
        topic = TranscriptTopic(
            title=data.title,
            summary=data.summary,
            transcript=data.transcript.text,
            timestamp=data.timestamp,
        )
        resp = transcript.add_event(event=event, data=topic)
        transcript.upsert_topic(topic)

    elif event == PipelineEvent.FINAL_SUMMARY:
        final_summary = TranscriptFinalSummary(summary=data.summary)
        resp = transcript.add_event(event=event, data=final_summary)
        transcript.summary = final_summary

    elif event == PipelineEvent.STATUS:
        resp = transcript.add_event(event=event, data=data)
        transcript.status = data.value

    else:
        logger.warning(f"Unknown event: {event}")
        return

    # transmit to websocket clients
    await ws_manager.send_json(transcript_id, resp.model_dump(mode="json"))


@router.post("/transcripts/{transcript_id}/record/webrtc")
async def transcript_record_webrtc(
    transcript_id: UUID, params: RtcOffer, request: Request
):
    transcript = transcripts_controller.get_by_id(transcript_id)
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
    )
