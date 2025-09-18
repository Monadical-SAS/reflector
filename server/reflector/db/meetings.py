from datetime import datetime
from typing import Any, Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from reflector.db.base import MeetingConsentModel, MeetingModel
from reflector.db.rooms import Room
from reflector.utils import generate_uuid4


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
    recording_trigger: Literal[
        "none", "prompt", "automatic", "automatic-2nd-participant"
    ] = "automatic-2nd-participant"
    num_clients: int = 0
    is_active: bool = True
    calendar_event_id: str | None = None
    calendar_metadata: dict[str, Any] | None = None


class MeetingController:
    async def create(
        self,
        session: AsyncSession,
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
        )
        new_meeting = MeetingModel(**meeting.model_dump())
        session.add(new_meeting)
        await session.commit()
        return meeting

    async def get_all_active(self, session: AsyncSession) -> list[Meeting]:
        query = select(MeetingModel).where(MeetingModel.is_active)
        result = await session.execute(query)
        return [Meeting(**row.__dict__) for row in result.scalars().all()]

    async def get_by_room_name(
        self,
        session: AsyncSession,
        room_name: str,
    ) -> Meeting | None:
        """
        Get a meeting by room name.
        For backward compatibility, returns the most recent meeting.
        """
        query = (
            select(MeetingModel)
            .where(MeetingModel.room_name == room_name)
            .order_by(MeetingModel.end_date.desc())
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Meeting(**row.__dict__)

    async def get_active(
        self, session: AsyncSession, room: Room, current_time: datetime
    ) -> Meeting | None:
        """
        Get latest active meeting for a room.
        For backward compatibility, returns the most recent active meeting.
        """
        query = (
            select(MeetingModel)
            .where(
                sa.and_(
                    MeetingModel.room_id == room.id,
                    MeetingModel.end_date > current_time,
                    MeetingModel.is_active,
                )
            )
            .order_by(MeetingModel.end_date.desc())
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Meeting(**row.__dict__)

    async def get_all_active_for_room(
        self, session: AsyncSession, room: Room, current_time: datetime
    ) -> list[Meeting]:
        query = (
            select(MeetingModel)
            .where(
                sa.and_(
                    MeetingModel.room_id == room.id,
                    MeetingModel.end_date > current_time,
                    MeetingModel.is_active,
                )
            )
            .order_by(MeetingModel.end_date.desc())
        )
        result = await session.execute(query)
        return [Meeting(**row.__dict__) for row in result.scalars().all()]

    async def get_active_by_calendar_event(
        self,
        session: AsyncSession,
        room: Room,
        calendar_event_id: str,
        current_time: datetime,
    ) -> Meeting | None:
        """
        Get active meeting for a specific calendar event.
        """
        query = select(MeetingModel).where(
            sa.and_(
                MeetingModel.room_id == room.id,
                MeetingModel.calendar_event_id == calendar_event_id,
                MeetingModel.end_date > current_time,
                MeetingModel.is_active,
            )
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Meeting(**row.__dict__)

    async def get_by_id(
        self, session: AsyncSession, meeting_id: str, **kwargs
    ) -> Meeting | None:
        query = select(MeetingModel).where(MeetingModel.id == meeting_id)
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Meeting(**row.__dict__)

    async def get_by_calendar_event(
        self, session: AsyncSession, calendar_event_id: str
    ) -> Meeting | None:
        query = select(MeetingModel).where(
            MeetingModel.calendar_event_id == calendar_event_id
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Meeting(**row.__dict__)

    async def update_meeting(self, session: AsyncSession, meeting_id: str, **kwargs):
        query = (
            update(MeetingModel).where(MeetingModel.id == meeting_id).values(**kwargs)
        )
        await session.execute(query)
        await session.commit()


class MeetingConsentController:
    async def get_by_meeting_id(
        self, session: AsyncSession, meeting_id: str
    ) -> list[MeetingConsent]:
        query = select(MeetingConsentModel).where(
            MeetingConsentModel.meeting_id == meeting_id
        )
        result = await session.execute(query)
        return [MeetingConsent(**row.__dict__) for row in result.scalars().all()]

    async def get_by_meeting_and_user(
        self, session: AsyncSession, meeting_id: str, user_id: str
    ) -> MeetingConsent | None:
        """Get existing consent for a specific user and meeting"""
        query = select(MeetingConsentModel).where(
            sa.and_(
                MeetingConsentModel.meeting_id == meeting_id,
                MeetingConsentModel.user_id == user_id,
            )
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return MeetingConsent(**row.__dict__)

    async def upsert(
        self, session: AsyncSession, consent: MeetingConsent
    ) -> MeetingConsent:
        if consent.user_id:
            # For authenticated users, check if consent already exists
            # not transactional but we're ok with that; the consents ain't deleted anyways
            existing = await self.get_by_meeting_and_user(
                session, consent.meeting_id, consent.user_id
            )
            if existing:
                query = (
                    update(MeetingConsentModel)
                    .where(MeetingConsentModel.id == existing.id)
                    .values(
                        consent_given=consent.consent_given,
                        consent_timestamp=consent.consent_timestamp,
                    )
                )
            await session.execute(query)
            await session.commit()

            existing.consent_given = consent.consent_given
            existing.consent_timestamp = consent.consent_timestamp
            return existing

        new_consent = MeetingConsentModel(**consent.model_dump())
        session.add(new_consent)
        await session.commit()
        return consent

    async def has_any_denial(self, session: AsyncSession, meeting_id: str) -> bool:
        """Check if any participant denied consent for this meeting"""
        query = select(MeetingConsentModel).where(
            sa.and_(
                MeetingConsentModel.meeting_id == meeting_id,
                MeetingConsentModel.consent_given.is_(False),
            )
        )
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        return row is not None


meetings_controller = MeetingController()
meeting_consent_controller = MeetingConsentController()
