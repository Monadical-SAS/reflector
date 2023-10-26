import json
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import sqlalchemy
from pydantic import BaseModel, Field
from reflector.db import database, metadata
from reflector.processors.types import Word as ProcessorWord
from reflector.settings import settings
from reflector.utils.audio_waveform import get_audio_waveform

transcripts = sqlalchemy.Table(
    "transcript",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("locked", sqlalchemy.Boolean),
    sqlalchemy.Column("duration", sqlalchemy.Integer),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime),
    sqlalchemy.Column("title", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("short_summary", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("long_summary", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("topics", sqlalchemy.JSON),
    sqlalchemy.Column("events", sqlalchemy.JSON),
    sqlalchemy.Column("source_language", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("target_language", sqlalchemy.String, nullable=True),
    # with user attached, optional
    sqlalchemy.Column("user_id", sqlalchemy.String),
)


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
        filter_empty: bool | None = True,
        filter_recording: bool | None = True,
    ) -> list[Transcript]:
        """
        Get all transcripts

        If `user_id` is specified, only return transcripts that belong to the user.
        Otherwise, return all anonymous transcripts.

        Parameters:
        - `order_by`: field to order by, e.g. "-created_at"
        - `filter_empty`: filter out empty transcripts
        - `filter_recording`: filter out transcripts that are currently recording
        """
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
        """
        Get a transcript by id
        """
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
        """
        Add a new transcript
        """
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
        """
        Update a transcript fields with key/values in values
        """
        query = (
            transcripts.update()
            .where(transcripts.c.id == transcript.id)
            .values(**values)
        )
        await database.execute(query)
        for key, value in values.items():
            setattr(transcript, key, value)

    async def remove_by_id(
        self,
        transcript_id: str,
        user_id: str | None = None,
    ) -> None:
        """
        Remove a transcript by id
        """
        transcript = await self.get_by_id(transcript_id, user_id=user_id)
        if not transcript:
            return
        if user_id is not None and transcript.user_id != user_id:
            return
        transcript.unlink()
        query = transcripts.delete().where(transcripts.c.id == transcript_id)
        await database.execute(query)

    @asynccontextmanager
    async def transaction(self):
        """
        A context manager for database transaction
        """
        async with database.transaction():
            yield

    async def append_event(
        self,
        transcript: Transcript,
        event: str,
        data: Any,
    ) -> TranscriptEvent:
        """
        Append an event to a transcript
        """
        resp = transcript.add_event(event=event, data=data)
        await self.update(transcript, {"events": transcript.events_dump()})
        return resp


transcripts_controller = TranscriptController()
