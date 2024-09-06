import json
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Literal
from uuid import uuid4

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from reflector.db import database, metadata
from reflector.processors.types import Word as ProcessorWord
from reflector.settings import settings
from reflector.storage import Storage
from sqlalchemy.sql import false

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
    sqlalchemy.Column("participants", sqlalchemy.JSON),
    sqlalchemy.Column("source_language", sqlalchemy.String, nullable=True),
    sqlalchemy.Column("target_language", sqlalchemy.String, nullable=True),
    sqlalchemy.Column(
        "reviewed", sqlalchemy.Boolean, nullable=False, server_default=false()
    ),
    sqlalchemy.Column(
        "audio_location",
        sqlalchemy.String,
        nullable=False,
        server_default="local",
    ),
    # with user attached, optional
    sqlalchemy.Column("user_id", sqlalchemy.String),
    sqlalchemy.Column(
        "share_mode",
        sqlalchemy.String,
        nullable=False,
        server_default="private",
    ),
    sqlalchemy.Column(
        "meeting_id",
        sqlalchemy.String,
    ),
    sqlalchemy.Column("zulip_message_id", sqlalchemy.Integer, nullable=True),
)


def generate_uuid4() -> str:
    return str(uuid4())


def generate_transcript_name() -> str:
    now = datetime.utcnow()
    return f"Transcript {now.strftime('%Y-%m-%d %H:%M:%S')}"


def get_storage() -> Storage:
    return Storage.get_instance(
        name=settings.TRANSCRIPT_STORAGE_BACKEND,
        settings_prefix="TRANSCRIPT_STORAGE_",
    )


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
    duration: float | None = 0
    transcript: str | None = None
    words: list[ProcessorWord] = []


class TranscriptFinalShortSummary(BaseModel):
    short_summary: str


class TranscriptFinalLongSummary(BaseModel):
    long_summary: str


class TranscriptFinalTitle(BaseModel):
    title: str


class TranscriptDuration(BaseModel):
    duration: float


class TranscriptWaveform(BaseModel):
    waveform: list[float]


class TranscriptEvent(BaseModel):
    event: str
    data: dict


class TranscriptParticipant(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str = Field(default_factory=generate_uuid4)
    speaker: int | None
    name: str


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
    participants: list[TranscriptParticipant] | None = []
    source_language: str = "en"
    target_language: str = "en"
    share_mode: Literal["private", "semi-private", "public"] = "private"
    audio_location: str = "local"
    reviewed: bool = False
    meeting_id: str | None = None
    zulip_message_id: int | None = None

    def add_event(self, event: str, data: BaseModel) -> TranscriptEvent:
        ev = TranscriptEvent(event=event, data=data.model_dump())
        self.events.append(ev)
        return ev

    def upsert_topic(self, topic: TranscriptTopic):
        index = next((i for i, t in enumerate(self.topics) if t.id == topic.id), None)
        if index is not None:
            self.topics[index] = topic
        else:
            self.topics.append(topic)

    def upsert_participant(self, participant: TranscriptParticipant):
        if self.participants:
            index = next(
                (i for i, p in enumerate(self.participants) if p.id == participant.id),
                None,
            )
            if index is not None:
                self.participants[index] = participant
            else:
                self.participants.append(participant)
        else:
            self.participants = [participant]
        return participant

    def delete_participant(self, participant_id: str):
        index = next(
            (i for i, p in enumerate(self.participants) if p.id == participant_id),
            None,
        )
        if index is not None:
            del self.participants[index]

    def events_dump(self, mode="json"):
        return [event.model_dump(mode=mode) for event in self.events]

    def topics_dump(self, mode="json"):
        return [topic.model_dump(mode=mode) for topic in self.topics]

    def participants_dump(self, mode="json"):
        return [participant.model_dump(mode=mode) for participant in self.participants]

    def unlink(self):
        if os.path.exists(self.data_path) and os.path.isdir(self.data_path):
            shutil.rmtree(self.data_path)

    @property
    def data_path(self):
        return Path(settings.DATA_DIR) / self.id

    @property
    def audio_wav_filename(self):
        return self.data_path / "audio.wav"

    @property
    def audio_mp3_filename(self):
        return self.data_path / "audio.mp3"

    @property
    def audio_waveform_filename(self):
        return self.data_path / "audio.json"

    @property
    def storage_audio_path(self):
        return f"{self.id}/audio.mp3"

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

    async def get_audio_url(self) -> str:
        if self.audio_location == "local":
            return self._generate_local_audio_link()
        elif self.audio_location == "storage":
            return await self._generate_storage_audio_link()
        raise Exception(f"Unknown audio location {self.audio_location}")

    async def _generate_storage_audio_link(self) -> str:
        return await get_storage().get_file_url(self.storage_audio_path)

    def _generate_local_audio_link(self) -> str:
        # we need to create an url to be used for diarization
        # we can't use the audio_mp3_filename because it's not accessible
        # from the diarization processor
        from datetime import timedelta

        from reflector.app import app
        from reflector.views.transcripts import create_access_token

        path = app.url_path_for(
            "transcript_get_audio_mp3",
            transcript_id=self.id,
        )
        url = f"{settings.BASE_URL}{path}"
        if self.user_id:
            # we pass token only if the user_id is set
            # otherwise, the audio is public
            token = create_access_token(
                {"sub": self.user_id},
                expires_delta=timedelta(minutes=15),
            )
            url += f"?token={token}"
        return url

    def find_empty_speaker(self) -> int:
        """
        Find an empty speaker seat
        """
        speakers = set(
            word.speaker
            for topic in self.topics
            for word in topic.words
            if word.speaker is not None
        )
        i = 0
        while True:
            if i not in speakers:
                return i
            i += 1
        raise Exception("No empty speaker found")


class TranscriptController:
    async def get_all(
        self,
        user_id: str | None = None,
        order_by: str | None = None,
        filter_empty: bool | None = False,
        filter_recording: bool | None = False,
        return_query: bool = False,
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

        if return_query:
            return query

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

    async def get_by_meeting_id(self, meeting_id: str, **kwargs) -> Transcript | None:
        """
        Get a transcript by meeting_id
        """
        query = transcripts.select().where(transcripts.c.meeting_id == meeting_id)
        if "user_id" in kwargs:
            query = query.where(transcripts.c.user_id == kwargs["user_id"])
        result = await database.fetch_one(query)
        if not result:
            return None
        return Transcript(**result)

    async def get_by_id_for_http(
        self,
        transcript_id: str,
        user_id: str | None,
    ) -> Transcript:
        """
        Get a transcript by ID for HTTP request.

        If not found, it will raise a 404 error.
        If the user is not allowed to access the transcript, it will raise a 403 error.

        This method checks the share mode of the transcript and the user_id
        to determine if the user can access the transcript.
        """
        query = transcripts.select().where(transcripts.c.id == transcript_id)
        result = await database.fetch_one(query)
        if not result:
            raise HTTPException(status_code=404, detail="Transcript not found")

        # if the transcript is anonymous, share mode is not checked
        transcript = Transcript(**result)
        if transcript.user_id is None:
            return transcript

        if transcript.share_mode == "private":
            # in private mode, only the owner can access the transcript
            if transcript.user_id == user_id:
                return transcript

        elif transcript.share_mode == "semi-private":
            # in semi-private mode, only the owner and the users with the link
            # can access the transcript
            if user_id is not None:
                return transcript

        elif transcript.share_mode == "public":
            # in public mode, everyone can access the transcript
            return transcript

        raise HTTPException(status_code=403, detail="Transcript access denied")

    async def add(
        self,
        name: str,
        source_language: str = "en",
        target_language: str = "en",
        user_id: str | None = None,
        meeting_id: str | None = None,
        share_mode: str = "private",
    ):
        """
        Add a new transcript
        """
        transcript = Transcript(
            name=name,
            source_language=source_language,
            target_language=target_language,
            user_id=user_id,
            meeting_id=meeting_id,
            share_mode=share_mode,
        )
        query = transcripts.insert().values(**transcript.model_dump())
        await database.execute(query)
        return transcript

    async def update(self, transcript: Transcript, values: dict, mutate=True):
        """
        Update a transcript fields with key/values in values
        """
        query = (
            transcripts.update()
            .where(transcripts.c.id == transcript.id)
            .values(**values)
        )
        await database.execute(query)
        if mutate:
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
        async with database.transaction(isolation="serializable"):
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
        await self.update(
            transcript,
            {"events": transcript.events_dump()},
            mutate=False,
        )
        return resp

    async def upsert_topic(
        self,
        transcript: Transcript,
        topic: TranscriptTopic,
    ) -> TranscriptEvent:
        """
        Append an event to a transcript
        """
        transcript.upsert_topic(topic)
        await self.update(
            transcript,
            {"topics": transcript.topics_dump()},
            mutate=False,
        )

    async def move_mp3_to_storage(self, transcript: Transcript):
        """
        Move mp3 file to storage
        """

        # store the audio on external storage
        await get_storage().put_file(
            transcript.storage_audio_path,
            transcript.audio_mp3_filename.read_bytes(),
        )

        # indicate on the transcript that the audio is now on storage
        await self.update(transcript, {"audio_location": "storage"})

        # unlink the local file
        transcript.audio_mp3_filename.unlink(missing_ok=True)

    async def upsert_participant(
        self,
        transcript: Transcript,
        participant: TranscriptParticipant,
    ) -> TranscriptParticipant:
        """
        Add/update a participant to a transcript
        """
        result = transcript.upsert_participant(participant)
        await self.update(
            transcript,
            {"participants": transcript.participants_dump()},
            mutate=False,
        )
        return result

    async def delete_participant(
        self,
        transcript: Transcript,
        participant_id: str,
    ):
        """
        Delete a participant from a transcript
        """
        transcript.delete_participant(participant_id)
        await self.update(
            transcript,
            {"participants": transcript.participants_dump()},
            mutate=False,
        )


transcripts_controller = TranscriptController()
