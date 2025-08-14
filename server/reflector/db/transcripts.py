import enum
import json
import logging
import os
import shutil
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

import sqlalchemy
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_serializer
from sqlalchemy import Enum
from sqlalchemy.dialects.postgresql import TSVECTOR
from sqlalchemy.sql import false, or_

from reflector.db import get_database, metadata
from reflector.db.recordings import recordings_controller
from reflector.db.rooms import rooms
from reflector.db.utils import is_postgresql
from reflector.processors.types import Word as ProcessorWord
from reflector.settings import settings
from reflector.storage import get_transcripts_storage, get_recordings_storage
from reflector.utils import generate_uuid4
from reflector.utils.webvtt import topics_to_webvtt

logger = logging.getLogger(__name__)


class SourceKind(enum.StrEnum):
    ROOM = enum.auto()
    LIVE = enum.auto()
    FILE = enum.auto()


transcripts = sqlalchemy.Table(
    "transcript",
    metadata,
    sqlalchemy.Column("id", sqlalchemy.String, primary_key=True),
    sqlalchemy.Column("name", sqlalchemy.String),
    sqlalchemy.Column("status", sqlalchemy.String),
    sqlalchemy.Column("locked", sqlalchemy.Boolean),
    sqlalchemy.Column("duration", sqlalchemy.Float),
    sqlalchemy.Column("created_at", sqlalchemy.DateTime(timezone=True)),
    sqlalchemy.Column("title", sqlalchemy.String),
    sqlalchemy.Column("short_summary", sqlalchemy.String),
    sqlalchemy.Column("long_summary", sqlalchemy.String),
    sqlalchemy.Column("topics", sqlalchemy.JSON),
    sqlalchemy.Column("events", sqlalchemy.JSON),
    sqlalchemy.Column("participants", sqlalchemy.JSON),
    sqlalchemy.Column("source_language", sqlalchemy.String),
    sqlalchemy.Column("target_language", sqlalchemy.String),
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
    sqlalchemy.Column("recording_id", sqlalchemy.String),
    sqlalchemy.Column("zulip_message_id", sqlalchemy.Integer),
    sqlalchemy.Column(
        "source_kind",
        Enum(SourceKind, values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    ),
    # indicative field: whether associated audio is deleted
    # the main "audio deleted" is the presence of the audio itself / consents not-given
    # same field could've been in recording/meeting, and it's maybe even ok to dupe it at need
    sqlalchemy.Column("audio_deleted", sqlalchemy.Boolean),
    sqlalchemy.Column("room_id", sqlalchemy.String),
    sqlalchemy.Column("webvtt", sqlalchemy.Text),
    sqlalchemy.Index("idx_transcript_recording_id", "recording_id"),
    sqlalchemy.Index("idx_transcript_user_id", "user_id"),
    sqlalchemy.Index("idx_transcript_created_at", "created_at"),
    sqlalchemy.Index("idx_transcript_user_id_recording_id", "user_id", "recording_id"),
    sqlalchemy.Index("idx_transcript_room_id", "room_id"),
)

# Add PostgreSQL-specific full-text search column
# This matches the migration in migrations/versions/116b2f287eab_add_full_text_search.py
if is_postgresql():
    transcripts.append_column(
        sqlalchemy.Column(
            "search_vector_en",
            TSVECTOR,
            sqlalchemy.Computed(
                "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
                "setweight(to_tsvector('english', coalesce(webvtt, '')), 'B')",
                persisted=True,
            ),
        )
    )
    # Add GIN index for the search vector
    transcripts.append_constraint(
        sqlalchemy.Index(
            "idx_transcript_search_vector_en",
            "search_vector_en",
            postgresql_using="gin",
        )
    )


def generate_transcript_name() -> str:
    now = datetime.now(timezone.utc)
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
    """Full transcript model with all fields."""

    id: str = Field(default_factory=generate_uuid4)
    user_id: str | None = None
    name: str = Field(default_factory=generate_transcript_name)
    status: str = "idle"
    duration: float = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str | None = None
    source_kind: SourceKind
    room_id: str | None = None
    locked: bool = False
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
    recording_id: str | None = None
    zulip_message_id: int | None = None
    audio_deleted: bool | None = None
    webvtt: str | None = None

    @field_serializer("created_at", when_used="json")
    def serialize_datetime(self, dt: datetime) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

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
        return await get_transcripts_storage().get_file_url(self.storage_audio_path)

    def _generate_local_audio_link(self) -> str:
        # we need to create an url to be used for diarization
        # we can't use the audio_mp3_filename because it's not accessible
        # from the diarization processor

        # TODO don't import app in db
        from reflector.app import app  # noqa: PLC0415

        # TODO a util + don''t import views in db
        from reflector.views.transcripts import create_access_token  # noqa: PLC0415

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
        source_kind: SourceKind | None = None,
        room_id: str | None = None,
        search_term: str | None = None,
        return_query: bool = False,
        exclude_columns: list[str] = ["topics", "events", "participants"],
    ) -> list[Transcript]:
        """
        Get all transcripts

        If `user_id` is specified, only return transcripts that belong to the user.
        Otherwise, return all anonymous transcripts.

        Parameters:
        - `order_by`: field to order by, e.g. "-created_at"
        - `filter_empty`: filter out empty transcripts
        - `filter_recording`: filter out transcripts that are currently recording
        - `room_id`: filter transcripts by room ID
        - `search_term`: filter transcripts by search term
        """

        query = transcripts.select().join(
            rooms, transcripts.c.room_id == rooms.c.id, isouter=True
        )

        if user_id:
            query = query.where(
                or_(transcripts.c.user_id == user_id, rooms.c.is_shared)
            )
        else:
            query = query.where(rooms.c.is_shared)

        if source_kind:
            query = query.where(transcripts.c.source_kind == source_kind)

        if room_id:
            query = query.where(transcripts.c.room_id == room_id)

        if search_term:
            query = query.where(transcripts.c.title.ilike(f"%{search_term}%"))

        # Exclude heavy JSON columns from list queries
        transcript_columns = [
            col for col in transcripts.c if col.name not in exclude_columns
        ]

        query = query.with_only_columns(
            transcript_columns
            + [
                rooms.c.name.label("room_name"),
            ]
        )

        if order_by is not None:
            field = getattr(transcripts.c, order_by[1:])
            if order_by.startswith("-"):
                field = field.desc()
            query = query.order_by(field)

        if filter_empty:
            query = query.filter(transcripts.c.status != "idle")

        if filter_recording:
            query = query.filter(transcripts.c.status != "recording")

        # print(query.compile(compile_kwargs={"literal_binds": True}))

        if return_query:
            return query

        results = await get_database().fetch_all(query)
        return results

    async def get_by_id(self, transcript_id: str, **kwargs) -> Transcript | None:
        """
        Get a transcript by id
        """
        query = transcripts.select().where(transcripts.c.id == transcript_id)
        if "user_id" in kwargs:
            query = query.where(transcripts.c.user_id == kwargs["user_id"])
        result = await get_database().fetch_one(query)
        if not result:
            return None
        return Transcript(**result)

    async def get_by_recording_id(
        self, recording_id: str, **kwargs
    ) -> Transcript | None:
        """
        Get a transcript by recording_id
        """
        query = transcripts.select().where(transcripts.c.recording_id == recording_id)
        if "user_id" in kwargs:
            query = query.where(transcripts.c.user_id == kwargs["user_id"])
        result = await get_database().fetch_one(query)
        if not result:
            return None
        return Transcript(**result)

    async def get_by_room_id(self, room_id: str, **kwargs) -> list[Transcript]:
        """
        Get transcripts by room_id (direct access without joins)
        """
        query = transcripts.select().where(transcripts.c.room_id == room_id)
        if "user_id" in kwargs:
            query = query.where(transcripts.c.user_id == kwargs["user_id"])
        if "order_by" in kwargs:
            order_by = kwargs["order_by"]
            field = getattr(transcripts.c, order_by[1:])
            if order_by.startswith("-"):
                field = field.desc()
            query = query.order_by(field)
        results = await get_database().fetch_all(query)
        return [Transcript(**result) for result in results]

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
        result = await get_database().fetch_one(query)
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
        source_kind: SourceKind,
        source_language: str = "en",
        target_language: str = "en",
        user_id: str | None = None,
        recording_id: str | None = None,
        share_mode: str = "private",
        meeting_id: str | None = None,
        room_id: str | None = None,
    ):
        """
        Add a new transcript
        """
        transcript = Transcript(
            name=name,
            source_kind=source_kind,
            source_language=source_language,
            target_language=target_language,
            user_id=user_id,
            recording_id=recording_id,
            share_mode=share_mode,
            meeting_id=meeting_id,
            room_id=room_id,
        )
        query = transcripts.insert().values(**transcript.model_dump())
        await get_database().execute(query)
        return transcript

    # TODO investigate why mutate= is used. it's used in one place currently, maybe because of ORM field updates.
    # using mutate=True is discouraged
    async def update(
        self, transcript: Transcript, values: dict, mutate=False
    ) -> Transcript:
        """
        Update a transcript fields with key/values in values.
        Returns a copy of the transcript with updated values.
        """
        values = TranscriptController._handle_topics_update(values)

        query = (
            transcripts.update()
            .where(transcripts.c.id == transcript.id)
            .values(**values)
        )
        await get_database().execute(query)
        if mutate:
            for key, value in values.items():
                setattr(transcript, key, value)

        updated_transcript = transcript.model_copy(update=values)
        return updated_transcript

    @staticmethod
    def _handle_topics_update(values: dict) -> dict:
        """Auto-update WebVTT when topics are updated."""

        if values.get("webvtt") is not None:
            logger.warn("trying to update read-only webvtt column")
            pass

        topics_data = values.get("topics")
        if topics_data is None:
            return values

        return {
            **values,
            "webvtt": topics_to_webvtt(
                [TranscriptTopic(**topic_dict) for topic_dict in topics_data]
            ),
        }

    async def remove_by_id(
        self,
        transcript_id: str,
        user_id: str | None = None,
    ) -> None:
        """
        Remove a transcript by id
        """
        transcript = await self.get_by_id(transcript_id)
        if not transcript:
            return
        if user_id is not None and transcript.user_id != user_id:
            return
        if transcript.audio_location == "storage" and not transcript.audio_deleted:
            try:
                await get_transcripts_storage().delete_file(
                    transcript.storage_audio_path
                )
            except Exception as e:
                logger.warning(
                    "Failed to delete transcript audio from storage",
                    error=str(e),
                    transcript_id=transcript.id,
                )
        transcript.unlink()
        if transcript.recording_id:
            try:
                recording = await recordings_controller.get_by_id(
                    transcript.recording_id
                )
                if recording:
                    try:
                        await get_recordings_storage().delete_file(recording.object_key)
                    except Exception as e:
                        logger.warning(
                            "Failed to delete recording object from S3",
                            error=str(e),
                            recording_id=transcript.recording_id,
                        )
                    await recordings_controller.remove_by_id(transcript.recording_id)
            except Exception as e:
                logger.warning(
                    "Failed to delete recording row",
                    error=str(e),
                    recording_id=transcript.recording_id,
                )
        query = transcripts.delete().where(transcripts.c.id == transcript_id)
        await get_database().execute(query)

    async def remove_by_recording_id(self, recording_id: str):
        """
        Remove a transcript by recording_id
        """
        query = transcripts.delete().where(transcripts.c.recording_id == recording_id)
        await get_database().execute(query)

    @asynccontextmanager
    async def transaction(self):
        """
        A context manager for database transaction
        """
        async with get_database().transaction(isolation="serializable"):
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

    async def upsert_topic(
        self,
        transcript: Transcript,
        topic: TranscriptTopic,
    ) -> TranscriptEvent:
        """
        Upsert topics to a transcript
        """
        transcript.upsert_topic(topic)
        await self.update(transcript, {"topics": transcript.topics_dump()})

    async def move_mp3_to_storage(self, transcript: Transcript):
        """
        Move mp3 file to storage
        """

        if transcript.audio_deleted:
            raise FileNotFoundError(
                f"Invalid state of transcript {transcript.id}: audio_deleted mark is set true"
            )

        if transcript.audio_location == "local":
            # store the audio on external storage if it's not already there
            if not transcript.audio_mp3_filename.exists():
                raise FileNotFoundError(
                    f"Audio file not found: {transcript.audio_mp3_filename}"
                )

            await get_transcripts_storage().put_file(
                transcript.storage_audio_path,
                transcript.audio_mp3_filename.read_bytes(),
            )

            # indicate on the transcript that the audio is now on storage
            # mutates transcript argument
            await self.update(transcript, {"audio_location": "storage"}, mutate=True)

        # unlink the local file
        transcript.audio_mp3_filename.unlink(missing_ok=True)

    async def download_mp3_from_storage(self, transcript: Transcript):
        """
        Download audio from storage
        """
        transcript.audio_mp3_filename.write_bytes(
            await get_transcripts_storage().get_file(
                transcript.storage_audio_path,
            )
        )

    async def upsert_participant(
        self,
        transcript: Transcript,
        participant: TranscriptParticipant,
    ) -> TranscriptParticipant:
        """
        Add/update a participant to a transcript
        """
        result = transcript.upsert_participant(participant)
        await self.update(transcript, {"participants": transcript.participants_dump()})
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
        await self.update(transcript, {"participants": transcript.participants_dump()})


transcripts_controller = TranscriptController()
