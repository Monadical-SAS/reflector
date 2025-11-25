"""Daily.co participant session tracking.

Stores webhook data for participant.joined and participant.left events to provide
historical session information (Daily.co API only returns current participants).
"""

from datetime import datetime

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert

from reflector.db import get_database, metadata
from reflector.utils.string import NonEmptyString

daily_participant_sessions = sa.Table(
    "daily_participant_session",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column(
        "meeting_id",
        sa.String,
        sa.ForeignKey("meeting.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column(
        "room_id",
        sa.String,
        sa.ForeignKey("room.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("session_id", sa.String, nullable=False),
    sa.Column("user_id", sa.String, nullable=True),
    sa.Column("user_name", sa.String, nullable=False),
    sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
    sa.Index("idx_daily_session_meeting_left", "meeting_id", "left_at"),
    sa.Index("idx_daily_session_room", "room_id"),
)


class DailyParticipantSession(BaseModel):
    """Daily.co participant session record.

    Tracks when a participant joined and left a meeting. Populated from webhooks:
    - participant.joined: Creates record with left_at=None
    - participant.left: Updates record with left_at

    ID format: {meeting_id}:{user_id}:{joined_at_ms}
    - Ensures idempotency (duplicate webhooks don't create duplicates)
    - Allows same user to rejoin (different joined_at = different session)

    Duration is calculated as: left_at - joined_at (not stored)
    """

    id: NonEmptyString
    meeting_id: NonEmptyString
    room_id: NonEmptyString
    session_id: NonEmptyString  # Daily.co's session_id (identifies room session)
    user_id: NonEmptyString | None = None
    user_name: str
    joined_at: datetime
    left_at: datetime | None = None


class DailyParticipantSessionController:
    """Controller for Daily.co participant session persistence."""

    async def get_by_id(self, id: str) -> DailyParticipantSession | None:
        """Get a session by its ID."""
        query = daily_participant_sessions.select().where(
            daily_participant_sessions.c.id == id
        )
        result = await get_database().fetch_one(query)
        return DailyParticipantSession(**result) if result else None

    async def get_open_session(
        self, meeting_id: NonEmptyString, session_id: NonEmptyString
    ) -> DailyParticipantSession | None:
        """Get the open (not left) session for a user in a meeting."""
        query = daily_participant_sessions.select().where(
            sa.and_(
                daily_participant_sessions.c.meeting_id == meeting_id,
                daily_participant_sessions.c.session_id == session_id,
                daily_participant_sessions.c.left_at.is_(None),
            )
        )
        results = await get_database().fetch_all(query)

        if len(results) > 1:
            raise ValueError(
                f"Multiple open sessions for daily session {session_id} in meeting {meeting_id}: "
                f"found {len(results)} sessions"
            )

        return DailyParticipantSession(**results[0]) if results else None

    async def upsert_joined(self, session: DailyParticipantSession) -> None:
        """Insert or update when participant.joined webhook arrives.

        Idempotent: Duplicate webhooks with same ID are safely ignored.
        Out-of-order: If left webhook arrived first, preserves left_at.
        """
        query = insert(daily_participant_sessions).values(**session.model_dump())
        query = query.on_conflict_do_update(
            index_elements=["id"],
            set_={"user_name": session.user_name},
        )
        await get_database().execute(query)

    async def upsert_left(self, session: DailyParticipantSession) -> None:
        """Update session when participant.left webhook arrives.

        Finds the open session for this user in this meeting and updates left_at.
        Works around Daily.co webhook timestamp inconsistency (joined_at differs by ~4ms between webhooks).

        Handles three cases:
        1. Normal flow: open session exists → updates left_at
        2. Out-of-order: left arrives first → creates new record with left data
        3. Duplicate: left arrives again → idempotent (DB trigger prevents left_at modification)
        """
        if session.left_at is None:
            raise ValueError("left_at is required for upsert_left")

        if session.left_at <= session.joined_at:
            raise ValueError(
                f"left_at ({session.left_at}) must be after joined_at ({session.joined_at})"
            )

        # Find existing open session (works around timestamp mismatch in webhooks)
        existing = await self.get_open_session(session.meeting_id, session.session_id)

        if existing:
            # Update existing open session
            query = (
                daily_participant_sessions.update()
                .where(daily_participant_sessions.c.id == existing.id)
                .values(left_at=session.left_at)
            )
            await get_database().execute(query)
        else:
            # Out-of-order or first webhook: insert new record
            query = insert(daily_participant_sessions).values(**session.model_dump())
            query = query.on_conflict_do_nothing(index_elements=["id"])
            await get_database().execute(query)

    async def get_by_meeting(self, meeting_id: str) -> list[DailyParticipantSession]:
        """Get all participant sessions for a meeting (active and ended)."""
        query = daily_participant_sessions.select().where(
            daily_participant_sessions.c.meeting_id == meeting_id
        )
        results = await get_database().fetch_all(query)
        return [DailyParticipantSession(**result) for result in results]

    async def get_active_by_meeting(
        self, meeting_id: str
    ) -> list[DailyParticipantSession]:
        """Get only active (not left) participant sessions for a meeting."""
        query = daily_participant_sessions.select().where(
            sa.and_(
                daily_participant_sessions.c.meeting_id == meeting_id,
                daily_participant_sessions.c.left_at.is_(None),
            )
        )
        results = await get_database().fetch_all(query)
        return [DailyParticipantSession(**result) for result in results]


daily_participant_sessions_controller = DailyParticipantSessionController()
