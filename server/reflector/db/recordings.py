from datetime import datetime
from typing import Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field

from reflector.db import database, metadata
from reflector.utils import generate_uuid4

recordings = sa.Table(
    "recording",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("bucket_name", sa.String, nullable=False),
    sa.Column("object_key", sa.String, nullable=False),
    sa.Column("recorded_at", sa.DateTime, nullable=False),
    sa.Column(
        "status",
        sa.String,
        nullable=False,
        server_default="pending",
    ),
    sa.Column("meeting_id", sa.String),
    sa.Index("idx_recording_meeting_id", "meeting_id"),
)


class Recording(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    bucket_name: str
    object_key: str
    recorded_at: datetime
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    meeting_id: str | None = None


class RecordingController:
    async def create(self, recording: Recording):
        query = recordings.insert().values(**recording.model_dump())
        await database.execute(query)
        return recording

    async def get_by_id(self, id: str) -> Recording:
        query = recordings.select().where(recordings.c.id == id)
        result = await database.fetch_one(query)
        return Recording(**result) if result else None

    async def get_by_object_key(self, bucket_name: str, object_key: str) -> Recording:
        query = recordings.select().where(
            recordings.c.bucket_name == bucket_name,
            recordings.c.object_key == object_key,
        )
        result = await database.fetch_one(query)
        return Recording(**result) if result else None


recordings_controller = RecordingController()
