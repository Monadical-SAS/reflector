from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TranscriptModel(Base):
    __tablename__ = "transcript"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(String)
    status: Mapped[Optional[str]] = mapped_column(String)
    locked: Mapped[Optional[bool]] = mapped_column(Boolean)
    duration: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    title: Mapped[Optional[str]] = mapped_column(String)
    short_summary: Mapped[Optional[str]] = mapped_column(String)
    long_summary: Mapped[Optional[str]] = mapped_column(String)
    topics: Mapped[Optional[list]] = mapped_column(JSON)
    events: Mapped[Optional[list]] = mapped_column(JSON)
    participants: Mapped[Optional[list]] = mapped_column(JSON)
    source_language: Mapped[Optional[str]] = mapped_column(String)
    target_language: Mapped[Optional[str]] = mapped_column(String)
    reviewed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    audio_location: Mapped[str] = mapped_column(
        String, nullable=False, server_default="local"
    )
    user_id: Mapped[Optional[str]] = mapped_column(String)
    share_mode: Mapped[str] = mapped_column(
        String, nullable=False, server_default="private"
    )
    meeting_id: Mapped[Optional[str]] = mapped_column(String)
    recording_id: Mapped[Optional[str]] = mapped_column(String)
    zulip_message_id: Mapped[Optional[int]] = mapped_column(Integer)
    source_kind: Mapped[str] = mapped_column(
        String, nullable=False
    )  # Enum will be handled separately
    audio_deleted: Mapped[Optional[bool]] = mapped_column(Boolean)
    room_id: Mapped[Optional[str]] = mapped_column(String)
    webvtt: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_transcript_recording_id", "recording_id"),
        Index("idx_transcript_user_id", "user_id"),
        Index("idx_transcript_created_at", "created_at"),
        Index("idx_transcript_user_id_recording_id", "user_id", "recording_id"),
        Index("idx_transcript_room_id", "room_id"),
        Index("idx_transcript_source_kind", "source_kind"),
        Index("idx_transcript_room_id_created_at", "room_id", "created_at"),
    )


from sqlalchemy import Computed

TranscriptModel.search_vector_en = Column(
    "search_vector_en",
    TSVECTOR,
    Computed(
        "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
        "setweight(to_tsvector('english', coalesce(long_summary, '')), 'B') || "
        "setweight(to_tsvector('english', coalesce(webvtt, '')), 'C')",
        persisted=True,
    ),
)


class RoomModel(Base):
    __tablename__ = "room"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    zulip_auto_post: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    zulip_stream: Mapped[Optional[str]] = mapped_column(String)
    zulip_topic: Mapped[Optional[str]] = mapped_column(String)
    is_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    room_mode: Mapped[str] = mapped_column(
        String, nullable=False, server_default="normal"
    )
    recording_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default="cloud"
    )
    recording_trigger: Mapped[str] = mapped_column(
        String, nullable=False, server_default="automatic-2nd-participant"
    )
    is_shared: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    webhook_url: Mapped[Optional[str]] = mapped_column(String)
    webhook_secret: Mapped[Optional[str]] = mapped_column(String)
    ics_url: Mapped[Optional[str]] = mapped_column(Text)
    ics_fetch_interval: Mapped[Optional[int]] = mapped_column(
        Integer, server_default=text("300")
    )
    ics_enabled: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ics_last_sync: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ics_last_etag: Mapped[Optional[str]] = mapped_column(Text)

    __table_args__ = (
        Index("idx_room_is_shared", "is_shared"),
        Index("idx_room_ics_enabled", "ics_enabled"),
    )


class MeetingModel(Base):
    __tablename__ = "meeting"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    room_name: Mapped[Optional[str]] = mapped_column(String)
    room_url: Mapped[Optional[str]] = mapped_column(String)
    host_room_url: Mapped[Optional[str]] = mapped_column(String)
    start_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    room_id: Mapped[Optional[str]] = mapped_column(
        String, ForeignKey("room.id", ondelete="CASCADE")
    )
    is_locked: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    room_mode: Mapped[str] = mapped_column(
        String, nullable=False, server_default="normal"
    )
    recording_type: Mapped[str] = mapped_column(
        String, nullable=False, server_default="cloud"
    )
    recording_trigger: Mapped[str] = mapped_column(
        String, nullable=False, server_default="automatic-2nd-participant"
    )
    num_clients: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    calendar_event_id: Mapped[Optional[str]] = mapped_column(
        String,
        ForeignKey(
            "calendar_event.id",
            ondelete="SET NULL",
            name="fk_meeting_calendar_event_id",
        ),
    )
    calendar_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    __table_args__ = (
        Index("idx_meeting_room_id", "room_id"),
        Index("idx_meeting_calendar_event", "calendar_event_id"),
    )


class MeetingConsentModel(Base):
    __tablename__ = "meeting_consent"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(
        String, ForeignKey("meeting.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(String)
    consent_given: Mapped[bool] = mapped_column(Boolean, nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )


class RecordingModel(Base):
    __tablename__ = "recording"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(
        String, ForeignKey("meeting.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(String, nullable=False)
    object_key: Mapped[str] = mapped_column(String, nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (Index("idx_recording_meeting_id", "meeting_id"),)


class CalendarEventModel(Base):
    __tablename__ = "calendar_event"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    room_id: Mapped[str] = mapped_column(
        String, ForeignKey("room.id", ondelete="CASCADE"), nullable=False
    )
    ics_uid: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    start_time: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attendees: Mapped[Optional[dict]] = mapped_column(JSONB)
    location: Mapped[Optional[str]] = mapped_column(Text)
    ics_raw_data: Mapped[Optional[str]] = mapped_column(Text)
    last_synced: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    __table_args__ = (Index("idx_calendar_event_room_start", "room_id", "start_time"),)


metadata = Base.metadata
