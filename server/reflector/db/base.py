from datetime import datetime
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TranscriptModel(Base):
    __tablename__ = "transcript"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    name: Mapped[Optional[str]] = mapped_column(sa.String)
    status: Mapped[Optional[str]] = mapped_column(sa.String)
    locked: Mapped[Optional[bool]] = mapped_column(sa.Boolean)
    duration: Mapped[Optional[float]] = mapped_column(sa.Float)
    created_at: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    title: Mapped[Optional[str]] = mapped_column(sa.String)
    short_summary: Mapped[Optional[str]] = mapped_column(sa.String)
    long_summary: Mapped[Optional[str]] = mapped_column(sa.String)
    topics: Mapped[Optional[list]] = mapped_column(sa.JSON)
    events: Mapped[Optional[list]] = mapped_column(sa.JSON)
    participants: Mapped[Optional[list]] = mapped_column(sa.JSON)
    source_language: Mapped[Optional[str]] = mapped_column(sa.String)
    target_language: Mapped[Optional[str]] = mapped_column(sa.String)
    reviewed: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    audio_location: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="local"
    )
    user_id: Mapped[Optional[str]] = mapped_column(sa.String)
    share_mode: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="private"
    )
    meeting_id: Mapped[Optional[str]] = mapped_column(sa.String)
    recording_id: Mapped[Optional[str]] = mapped_column(sa.String)
    zulip_message_id: Mapped[Optional[int]] = mapped_column(sa.Integer)
    source_kind: Mapped[str] = mapped_column(
        sa.String, nullable=False
    )  # Enum will be handled separately
    audio_deleted: Mapped[Optional[bool]] = mapped_column(sa.Boolean)
    room_id: Mapped[Optional[str]] = mapped_column(sa.String)
    webvtt: Mapped[Optional[str]] = mapped_column(sa.Text)

    __table_args__ = (
        sa.Index("idx_transcript_recording_id", "recording_id"),
        sa.Index("idx_transcript_user_id", "user_id"),
        sa.Index("idx_transcript_created_at", "created_at"),
        sa.Index("idx_transcript_user_id_recording_id", "user_id", "recording_id"),
        sa.Index("idx_transcript_room_id", "room_id"),
        sa.Index("idx_transcript_source_kind", "source_kind"),
        sa.Index("idx_transcript_room_id_created_at", "room_id", "created_at"),
    )


TranscriptModel.search_vector_en = sa.Column(
    "search_vector_en",
    TSVECTOR,
    sa.Computed(
        "setweight(to_tsvector('english', coalesce(title, '')), 'A') || "
        "setweight(to_tsvector('english', coalesce(long_summary, '')), 'B') || "
        "setweight(to_tsvector('english', coalesce(webvtt, '')), 'C')",
        persisted=True,
    ),
)


class RoomModel(Base):
    __tablename__ = "room"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    name: Mapped[str] = mapped_column(sa.String, nullable=False, unique=True)
    user_id: Mapped[str] = mapped_column(sa.String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    zulip_auto_post: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    zulip_stream: Mapped[Optional[str]] = mapped_column(sa.String)
    zulip_topic: Mapped[Optional[str]] = mapped_column(sa.String)
    is_locked: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    room_mode: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="normal"
    )
    recording_type: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="cloud"
    )
    recording_trigger: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="automatic-2nd-participant"
    )
    is_shared: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    webhook_url: Mapped[Optional[str]] = mapped_column(sa.String)
    webhook_secret: Mapped[Optional[str]] = mapped_column(sa.String)
    ics_url: Mapped[Optional[str]] = mapped_column(sa.Text)
    ics_fetch_interval: Mapped[Optional[int]] = mapped_column(
        sa.Integer, server_default=sa.text("300")
    )
    ics_enabled: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    ics_last_sync: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True)
    )
    ics_last_etag: Mapped[Optional[str]] = mapped_column(sa.Text)

    __table_args__ = (
        sa.Index("idx_room_is_shared", "is_shared"),
        sa.Index("idx_room_ics_enabled", "ics_enabled"),
    )


class MeetingModel(Base):
    __tablename__ = "meeting"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    room_name: Mapped[Optional[str]] = mapped_column(sa.String)
    room_url: Mapped[Optional[str]] = mapped_column(sa.String)
    host_room_url: Mapped[Optional[str]] = mapped_column(sa.String)
    start_date: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    end_date: Mapped[Optional[datetime]] = mapped_column(sa.DateTime(timezone=True))
    room_id: Mapped[Optional[str]] = mapped_column(
        sa.String, sa.ForeignKey("room.id", ondelete="CASCADE")
    )
    is_locked: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    room_mode: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="normal"
    )
    recording_type: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="cloud"
    )
    recording_trigger: Mapped[str] = mapped_column(
        sa.String, nullable=False, server_default="automatic-2nd-participant"
    )
    num_clients: Mapped[int] = mapped_column(
        sa.Integer, nullable=False, server_default=sa.text("0")
    )
    is_active: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("true")
    )
    calendar_event_id: Mapped[Optional[str]] = mapped_column(
        sa.String,
        sa.ForeignKey(
            "calendar_event.id",
            ondelete="SET NULL",
            name="fk_meeting_calendar_event_id",
        ),
    )
    calendar_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)

    __table_args__ = (
        sa.Index("idx_meeting_room_id", "room_id"),
        sa.Index("idx_meeting_calendar_event", "calendar_event_id"),
    )


class MeetingConsentModel(Base):
    __tablename__ = "meeting_consent"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("meeting.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[Optional[str]] = mapped_column(sa.String)
    consent_given: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    consent_timestamp: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )


class RecordingModel(Base):
    __tablename__ = "recording"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    meeting_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("meeting.id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(sa.String, nullable=False)
    object_key: Mapped[str] = mapped_column(sa.String, nullable=False)
    duration: Mapped[Optional[float]] = mapped_column(sa.Float)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

    __table_args__ = (sa.Index("idx_recording_meeting_id", "meeting_id"),)


class CalendarEventModel(Base):
    __tablename__ = "calendar_event"

    id: Mapped[str] = mapped_column(sa.String, primary_key=True)
    room_id: Mapped[str] = mapped_column(
        sa.String, sa.ForeignKey("room.id", ondelete="CASCADE"), nullable=False
    )
    ics_uid: Mapped[str] = mapped_column(sa.Text, nullable=False)
    title: Mapped[Optional[str]] = mapped_column(sa.Text)
    description: Mapped[Optional[str]] = mapped_column(sa.Text)
    start_time: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    end_time: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    attendees: Mapped[Optional[dict]] = mapped_column(JSONB)
    location: Mapped[Optional[str]] = mapped_column(sa.Text)
    ics_raw_data: Mapped[Optional[str]] = mapped_column(sa.Text)
    last_synced: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    is_deleted: Mapped[bool] = mapped_column(
        sa.Boolean, nullable=False, server_default=sa.text("false")
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

    __table_args__ = (
        sa.Index("idx_calendar_event_room_start", "room_id", "start_time"),
    )


metadata = Base.metadata
