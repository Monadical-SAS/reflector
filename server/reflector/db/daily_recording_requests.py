from datetime import datetime
from typing import Literal
from uuid import UUID

import sqlalchemy as sa
from pydantic import BaseModel
from sqlalchemy.dialects.postgresql import insert

from reflector.db import get_database, metadata
from reflector.utils.string import NonEmptyString

daily_recording_requests = sa.Table(
    "daily_recording_request",
    metadata,
    sa.Column("recording_id", sa.String, primary_key=True),
    sa.Column(
        "meeting_id",
        sa.String,
        sa.ForeignKey("meeting.id", ondelete="CASCADE"),
        nullable=False,
    ),
    sa.Column("instance_id", sa.String, nullable=False),
    sa.Column("type", sa.String, nullable=False),
    sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
    sa.Index("idx_meeting_id", "meeting_id"),
    sa.Index("idx_instance_id", "instance_id"),
)


class DailyRecordingRequest(BaseModel):
    recording_id: NonEmptyString
    meeting_id: NonEmptyString
    instance_id: UUID
    type: Literal["cloud", "raw-tracks"]
    requested_at: datetime


class DailyRecordingRequestsController:
    async def create(self, request: DailyRecordingRequest) -> None:
        stmt = insert(daily_recording_requests).values(
            recording_id=request.recording_id,
            meeting_id=request.meeting_id,
            instance_id=str(request.instance_id),
            type=request.type,
            requested_at=request.requested_at,
        )
        stmt = stmt.on_conflict_do_nothing(index_elements=["recording_id"])
        await get_database().execute(stmt)

    async def find_by_recording_id(
        self,
        recording_id: NonEmptyString,
    ) -> tuple[NonEmptyString, Literal["cloud", "raw-tracks"]] | None:
        query = daily_recording_requests.select().where(
            daily_recording_requests.c.recording_id == recording_id
        )
        result = await get_database().fetch_one(query)

        if not result:
            return None

        req = DailyRecordingRequest(
            recording_id=result["recording_id"],
            meeting_id=result["meeting_id"],
            instance_id=UUID(result["instance_id"]),
            type=result["type"],
            requested_at=result["requested_at"],
        )
        return (req.meeting_id, req.type)

    async def find_by_instance_id(
        self,
        instance_id: UUID,
    ) -> list[DailyRecordingRequest]:
        """Multiple recordings can have same instance_id (stop/restart)."""
        query = daily_recording_requests.select().where(
            daily_recording_requests.c.instance_id == str(instance_id)
        )
        results = await get_database().fetch_all(query)
        return [
            DailyRecordingRequest(
                recording_id=r["recording_id"],
                meeting_id=r["meeting_id"],
                instance_id=UUID(r["instance_id"]),
                type=r["type"],
                requested_at=r["requested_at"],
            )
            for r in results
        ]

    async def get_by_meeting_id(
        self,
        meeting_id: NonEmptyString,
    ) -> list[DailyRecordingRequest]:
        query = daily_recording_requests.select().where(
            daily_recording_requests.c.meeting_id == meeting_id
        )
        results = await get_database().fetch_all(query)
        return [
            DailyRecordingRequest(
                recording_id=r["recording_id"],
                meeting_id=r["meeting_id"],
                instance_id=UUID(r["instance_id"]),
                type=r["type"],
                requested_at=r["requested_at"],
            )
            for r in results
        ]


daily_recording_requests_controller = DailyRecordingRequestsController()
