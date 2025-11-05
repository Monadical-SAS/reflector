from datetime import datetime
from typing import Any, Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import JSONB

from reflector.db import get_database, metadata
from reflector.db.rooms import Room, rooms
from reflector.platform_types import Platform
from reflector.utils import generate_uuid4
from reflector.video_platforms.factory import get_platform

meetings = sa.Table(
    "meeting",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("room_name", sa.String),
    sa.Column("room_url", sa.String),
    sa.Column("host_room_url", sa.String),
    sa.Column("start_date", sa.DateTime(timezone=True)),
    sa.Column("end_date", sa.DateTime(timezone=True)),
    sa.Column(
        "room_id",
        sa.String,
        sa.ForeignKey("room.id", ondelete="CASCADE"),
        nullable=True,
    ),
    sa.Column("is_locked", sa.Boolean, nullable=False, server_default=sa.false()),
    sa.Column("room_mode", sa.String, nullable=False, server_default="normal"),
    sa.Column("recording_type", sa.String, nullable=False, server_default="cloud"),
    sa.Column(
        "recording_trigger",
        sa.String,
        nullable=False,
        server_default="automatic-2nd-participant",
    ),
    sa.Column(
        "num_clients",
        sa.Integer,
        nullable=False,
        server_default=sa.text("0"),
    ),
    sa.Column(
        "is_active",
        sa.Boolean,
        nullable=False,
        server_default=sa.true(),
    ),
    sa.Column(
        "calendar_event_id",
        sa.String,
        sa.ForeignKey(
            "calendar_event.id",
            ondelete="SET NULL",
            name="fk_meeting_calendar_event_id",
        ),
    ),
    sa.Column("calendar_metadata", JSONB),
    sa.Column(
        "platform",
        sa.String,
        nullable=False,
        server_default="whereby",
    ),
    sa.Index("idx_meeting_room_id", "room_id"),
    sa.Index("idx_meeting_calendar_event", "calendar_event_id"),
)

meeting_consent = sa.Table(
    "meeting_consent",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column(
        "meeting_id",
        sa.String,
        sa.ForeignKey("meeting.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("user_id", sa.String),
    sa.Column("consent_given", sa.Boolean, nullable=False),
    sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=False),
)


class MeetingConsent(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    meeting_id: str
    user_id: str | None = None
    consent_given: bool
    consent_timestamp: datetime


class Meeting(BaseModel):
    id: str
    room_name: str
    room_url: str
    host_room_url: str
    start_date: datetime
    end_date: datetime
    room_id: str | None
    is_locked: bool = False
    room_mode: Literal["normal", "group"] = "normal"
    recording_type: Literal["none", "local", "cloud"] = "cloud"
    recording_trigger: Literal[  # whereby-specific
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    num_clients: int = 0
    is_active: bool = True
    calendar_event_id: str | None = None
    calendar_metadata: dict[str, Any] | None = None
    platform: Platform = "whereby"


class MeetingController:
    async def create(
        self,
        id: str,
        room_name: str,
        room_url: str,
        host_room_url: str,
        start_date: datetime,
        end_date: datetime,
        room: Room,
        calendar_event_id: str | None = None,
        calendar_metadata: dict[str, Any] | None = None,
    ):
        meeting = Meeting(
            id=id,
            room_name=room_name,
            room_url=room_url,
            host_room_url=host_room_url,
            start_date=start_date,
            end_date=end_date,
            room_id=room.id,
            is_locked=room.is_locked,
            room_mode=room.room_mode,
            recording_type=room.recording_type,
            recording_trigger=room.recording_trigger,
            calendar_event_id=calendar_event_id,
            calendar_metadata=calendar_metadata,
            platform=get_platform(room.platform),
        )
        query = meetings.insert().values(**meeting.model_dump())
        await get_database().execute(query)
        return meeting

    async def get_all_active(self) -> list[Meeting]:
        query = (
            sa.select(meetings, rooms.c.platform.label("room_platform"))
            .select_from(meetings.outerjoin(rooms, meetings.c.room_id == rooms.c.id))
            .where(meetings.c.is_active)
        )
        results = await get_database().fetch_all(query)

        enhanced_meetings = []
        for result in results:
            meeting_data = {k: v for k, v in result.items() if k != "room_platform"}
            meeting = Meeting(**meeting_data)
            self._enhance_with_room(meeting, result["room_platform"])
            enhanced_meetings.append(meeting)

        return enhanced_meetings

    async def get_by_room_name(
        self,
        room_name: str,
    ) -> Meeting | None:
        """
        Get a meeting by room name.
        For backward compatibility, returns the most recent meeting.
        """
        query = (
            sa.select(meetings, rooms.c.platform.label("room_platform"))
            .select_from(meetings.outerjoin(rooms, meetings.c.room_id == rooms.c.id))
            .where(meetings.c.room_name == room_name)
            .order_by(meetings.c.end_date.desc())
        )
        result = await get_database().fetch_one(query)
        if not result:
            return None

        meeting_data = {k: v for k, v in result.items() if k != "room_platform"}
        meeting = Meeting(**meeting_data)
        self._enhance_with_room(meeting, result["room_platform"])
        return meeting

    async def get_active(self, room: Room, current_time: datetime) -> Meeting | None:
        """
        Get latest active meeting for a room.
        For backward compatibility, returns the most recent active meeting.
        """
        end_date = getattr(meetings.c, "end_date")
        query = (
            meetings.select()
            .where(
                sa.and_(
                    meetings.c.room_id == room.id,
                    meetings.c.end_date > current_time,
                    meetings.c.is_active,
                )
            )
            .order_by(end_date.desc())
        )
        result = await get_database().fetch_one(query)
        if not result:
            return None

        return self._enhance_with_room(Meeting(**result), room)

    async def get_all_active_for_room(
        self, room: Room, current_time: datetime
    ) -> list[Meeting]:
        end_date = getattr(meetings.c, "end_date")
        query = (
            meetings.select()
            .where(
                sa.and_(
                    meetings.c.room_id == room.id,
                    meetings.c.end_date > current_time,
                    meetings.c.is_active,
                )
            )
            .order_by(end_date.desc())
        )
        results = await get_database().fetch_all(query)
        return [self._enhance_with_room(Meeting(**result), room) for result in results]

    async def get_active_by_calendar_event(
        self, room: Room, calendar_event_id: str, current_time: datetime
    ) -> Meeting | None:
        """
        Get active meeting for a specific calendar event.
        """
        query = meetings.select().where(
            sa.and_(
                meetings.c.room_id == room.id,
                meetings.c.calendar_event_id == calendar_event_id,
                meetings.c.end_date > current_time,
                meetings.c.is_active,
            )
        )
        result = await get_database().fetch_one(query)
        if not result:
            return None
        return self._enhance_with_room(Meeting(**result), room)

    async def get_by_id(
        self, meeting_id: str, room: Room | None = None
    ) -> Meeting | None:
        query = meetings.select().where(meetings.c.id == meeting_id)

        if room:
            query = query.where(meetings.c.room_id == room.id)

        result = await get_database().fetch_one(query)
        if not result:
            return None

        meeting = Meeting(**result)

        if room:
            self._enhance_with_room(meeting, room)

        return meeting

    async def get_by_calendar_event(
        self, calendar_event_id: str, room: Room
    ) -> Meeting | None:
        query = meetings.select().where(
            meetings.c.calendar_event_id == calendar_event_id
        )
        if room:
            query = query.where(meetings.c.room_id == room.id)
        result = await get_database().fetch_one(query)
        if not result:
            return None
        return Meeting(**result)

    async def update_meeting(self, meeting_id: str, **kwargs):
        query = meetings.update().where(meetings.c.id == meeting_id).values(**kwargs)
        await get_database().execute(query)

    async def increment_num_clients(self, meeting_id: str) -> None:
        """Atomically increment participant count."""
        query = (
            meetings.update()
            .where(meetings.c.id == meeting_id)
            .values(num_clients=meetings.c.num_clients + 1)
        )
        await get_database().execute(query)

    async def decrement_num_clients(self, meeting_id: str) -> None:
        """Atomically decrement participant count (min 0)."""
        query = (
            meetings.update()
            .where(meetings.c.id == meeting_id)
            .values(
                num_clients=sa.case(
                    (meetings.c.num_clients > 0, meetings.c.num_clients - 1), else_=0
                )
            )
        )
        await get_database().execute(query)

    # MUTATES the argument, only for internal use
    @staticmethod
    def _enhance_with_room(meeting: Meeting, room_platform: Platform | None) -> Meeting:
        meeting.platform = meeting.platform or get_platform(room_platform)
        return meeting


class MeetingConsentController:
    async def get_by_meeting_id(self, meeting_id: str) -> list[MeetingConsent]:
        query = meeting_consent.select().where(
            meeting_consent.c.meeting_id == meeting_id
        )
        results = await get_database().fetch_all(query)
        return [MeetingConsent(**result) for result in results]

    async def get_by_meeting_and_user(
        self, meeting_id: str, user_id: str
    ) -> MeetingConsent | None:
        """Get existing consent for a specific user and meeting"""
        query = meeting_consent.select().where(
            meeting_consent.c.meeting_id == meeting_id,
            meeting_consent.c.user_id == user_id,
        )
        result = await get_database().fetch_one(query)
        if result is None:
            return None
        return MeetingConsent(**result)

    async def upsert(self, consent: MeetingConsent) -> MeetingConsent:
        if consent.user_id:
            # For authenticated users, check if consent already exists
            # not transactional but we're ok with that; the consents ain't deleted anyways
            existing = await self.get_by_meeting_and_user(
                consent.meeting_id, consent.user_id
            )
            if existing:
                query = (
                    meeting_consent.update()
                    .where(meeting_consent.c.id == existing.id)
                    .values(
                        consent_given=consent.consent_given,
                        consent_timestamp=consent.consent_timestamp,
                    )
                )
                await get_database().execute(query)

                existing.consent_given = consent.consent_given
                existing.consent_timestamp = consent.consent_timestamp
                return existing

        query = meeting_consent.insert().values(**consent.model_dump())
        await get_database().execute(query)
        return consent

    async def has_any_denial(self, meeting_id: str) -> bool:
        """Check if any participant denied consent for this meeting"""
        query = meeting_consent.select().where(
            meeting_consent.c.meeting_id == meeting_id,
            meeting_consent.c.consent_given.is_(False),
        )
        result = await get_database().fetch_one(query)
        return result is not None


meetings_controller = MeetingController()
meeting_consent_controller = MeetingConsentController()
