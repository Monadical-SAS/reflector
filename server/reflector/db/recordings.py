from datetime import datetime

from pydantic import BaseModel, Field
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from reflector.db.base import RecordingModel
from reflector.utils import generate_uuid4


class Recording(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    meeting_id: str
    url: str
    object_key: str
    duration: float | None = None
    created_at: datetime


class RecordingController:
    async def create(
        self,
        session: AsyncSession,
        meeting_id: str,
        url: str,
        object_key: str,
        duration: float | None = None,
        created_at: datetime | None = None,
    ):
        if created_at is None:
            from datetime import timezone

            created_at = datetime.now(timezone.utc)

        recording = Recording(
            meeting_id=meeting_id,
            url=url,
            object_key=object_key,
            duration=duration,
            created_at=created_at,
        )
        new_recording = RecordingModel(**recording.model_dump())
        session.add(new_recording)
        await session.commit()
        return recording

    async def get_by_id(
        self, session: AsyncSession, recording_id: str
    ) -> Recording | None:
        """
        Get a recording by id
        """
        query = select(RecordingModel).where(RecordingModel.id == recording_id)
        result = await session.execute(query)
        row = result.scalar_one_or_none()
        if not row:
            return None
        return Recording(**row.__dict__)

    async def get_by_meeting_id(
        self, session: AsyncSession, meeting_id: str
    ) -> list[Recording]:
        """
        Get all recordings for a meeting
        """
        query = select(RecordingModel).where(RecordingModel.meeting_id == meeting_id)
        result = await session.execute(query)
        return [Recording(**row.__dict__) for row in result.scalars().all()]

    async def remove_by_id(self, session: AsyncSession, recording_id: str) -> None:
        """
        Remove a recording by id
        """
        query = delete(RecordingModel).where(RecordingModel.id == recording_id)
        await session.execute(query)
        await session.commit()


recordings_controller = RecordingController()
