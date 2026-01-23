from datetime import datetime, timedelta
from typing import Any, Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy.dialects.postgresql import JSONB

from reflector.db import get_database, metadata
from reflector.db.rooms import Room
from reflector.schemas.platform import WHEREBY_PLATFORM, Platform
from reflector.utils import generate_uuid4
from reflector.utils.string import NonEmptyString, assert_equal

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
        server_default=assert_equal(WHEREBY_PLATFORM, "whereby"),
    ),
    # Daily.co composed video (Brady Bunch grid layout) - Daily.co only, not Whereby
    sa.Column("daily_composed_video_s3_key", sa.String, nullable=True),
    sa.Column("daily_composed_video_duration", sa.Integer, nullable=True),
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
    platform: Platform = WHEREBY_PLATFORM
    # Daily.co composed video (Brady Bunch grid) - Daily.co only
    daily_composed_video_s3_key: str | None = None
    daily_composed_video_duration: int | None = None


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
            platform=room.platform,
        )
        query = meetings.insert().values(**meeting.model_dump())
        await get_database().execute(query)
        return meeting

    async def get_all_active(self, platform: str | None = None) -> list[Meeting]:
        conditions = [meetings.c.is_active]
        if platform is not None:
            conditions.append(meetings.c.platform == platform)
        query = meetings.select().where(sa.and_(*conditions))
        results = await get_database().fetch_all(query)
        return [Meeting(**result) for result in results]

    async def get_by_room_name(
        self,
        room_name: str,
    ) -> Meeting | None:
        """
        Get a meeting by room name.
        For backward compatibility, returns the most recent meeting.
        """
        query = (
            meetings.select()
            .where(meetings.c.room_name == room_name)
            .order_by(meetings.c.end_date.desc())
        )
        result = await get_database().fetch_one(query)
        if not result:
            return None
        return Meeting(**result)

    async def get_by_room_name_all(self, room_name: str) -> list[Meeting]:
        """Get all meetings for a room name (not just most recent)."""
        query = meetings.select().where(meetings.c.room_name == room_name)
        results = await get_database().fetch_all(query)
        return [Meeting(**r) for r in results]

    async def get_by_room_name_and_time(
        self,
        room_name: NonEmptyString,
        recording_start: datetime,
        time_window_hours: int = 168,
    ) -> Meeting | None:
        """
        Get meeting by room name closest to recording timestamp.

        HACK ALERT: Daily.co doesn't return instanceId in recordings API response,
        and mtgSessionId is separate from our instanceId. Time-based matching is
        the least-bad workaround.

        This handles edge case of duplicate room_name values in DB (race conditions,
        double-clicks, etc.) by matching based on temporal proximity.

        Algorithm:
        1. Find meetings within time_window_hours of recording_start
        2. Return meeting with start_date closest to recording_start
        3. If tie, return first by meeting.id (deterministic)

        Args:
            room_name: Daily.co room name from recording
            recording_start: Timezone-aware datetime from recording.start_ts
            time_window_hours: Search window (default 168 = 1 week)

        Returns:
            Meeting closest to recording timestamp, or None if no matches

        Failure modes:
        - Multiple meetings in same room within ~5 minutes: picks closest
        - All meetings outside time window: returns None
        - Clock skew between Daily.co and DB: 1-week window tolerates this

        Why 1 week window:
        - Handles webhook failures (recording discovered days later)
        - Tolerates clock skew
        - Rejects unrelated meetings from weeks ago

        """
        # Validate timezone-aware datetime
        if recording_start.tzinfo is None:
            raise ValueError(
                f"recording_start must be timezone-aware, got naive datetime: {recording_start}"
            )

        window_start = recording_start - timedelta(hours=time_window_hours)
        window_end = recording_start + timedelta(hours=time_window_hours)

        query = (
            meetings.select()
            .where(
                sa.and_(
                    meetings.c.room_name == room_name,
                    meetings.c.start_date >= window_start,
                    meetings.c.start_date <= window_end,
                )
            )
            .order_by(meetings.c.start_date)
        )

        results = await get_database().fetch_all(query)
        if not results:
            return None

        candidates = [Meeting(**r) for r in results]

        # Find meeting with start_date closest to recording_start
        closest = min(
            candidates,
            key=lambda m: (
                abs((m.start_date - recording_start).total_seconds()),
                m.id,  # Tie-breaker: deterministic by UUID
            ),
        )

        return closest

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
        return Meeting(**result)

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
        return [Meeting(**result) for result in results]

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
        return Meeting(**result)

    async def get_by_id(
        self, meeting_id: str, room: Room | None = None
    ) -> Meeting | None:
        query = meetings.select().where(meetings.c.id == meeting_id)

        if room:
            query = query.where(meetings.c.room_id == room.id)

        result = await get_database().fetch_one(query)
        if not result:
            return None
        return Meeting(**result)

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

    async def set_cloud_recording_if_missing(
        self,
        meeting_id: NonEmptyString,
        s3_key: NonEmptyString,
        duration: int,
    ) -> bool:
        """
        Set cloud recording only if not already set.

        Returns True if updated, False if already set.
        Prevents webhook/polling race condition via atomic WHERE clause.
        """
        # Check current value before update to detect actual change
        meeting_before = await self.get_by_id(meeting_id)
        if not meeting_before:
            return False

        was_null = meeting_before.daily_composed_video_s3_key is None

        query = (
            meetings.update()
            .where(
                sa.and_(
                    meetings.c.id == meeting_id,
                    meetings.c.daily_composed_video_s3_key.is_(None),
                )
            )
            .values(
                daily_composed_video_s3_key=s3_key,
                daily_composed_video_duration=duration,
            )
        )
        await get_database().execute(query)

        # Return True only if value was NULL before (actual update occurred)
        # If was_null=False, the WHERE clause prevented the update
        return was_null

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
