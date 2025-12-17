from datetime import datetime
from typing import Literal

import sqlalchemy as sa
from pydantic import BaseModel, Field
from sqlalchemy import or_

from reflector.db import get_database, metadata
from reflector.utils import generate_uuid4

recordings = sa.Table(
    "recording",
    metadata,
    sa.Column("id", sa.String, primary_key=True),
    sa.Column("bucket_name", sa.String, nullable=False),
    sa.Column("object_key", sa.String, nullable=False),
    sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
    sa.Column(
        "status",
        sa.String,
        nullable=False,
        server_default="pending",
    ),
    sa.Column("meeting_id", sa.String),
    sa.Column("track_keys", sa.JSON, nullable=True),
    sa.Index("idx_recording_meeting_id", "meeting_id"),
)


class Recording(BaseModel):
    id: str = Field(default_factory=generate_uuid4)
    bucket_name: str
    object_key: str
    recorded_at: datetime
    status: Literal["pending", "processing", "completed", "failed"] = "pending"
    meeting_id: str | None = None
    # track_keys can be empty list [] if recording finished but no audio was captured (silence/muted)
    # None means not a multitrack recording, [] means multitrack with no tracks
    track_keys: list[str] | None = None

    @property
    def is_multitrack(self) -> bool:
        """True if recording has separate audio tracks (1+ tracks counts as multitrack)."""
        return self.track_keys is not None and len(self.track_keys) > 0


class RecordingController:
    async def create(self, recording: Recording):
        query = recordings.insert().values(**recording.model_dump())
        await get_database().execute(query)
        return recording

    async def get_by_id(self, id: str) -> Recording | None:
        query = recordings.select().where(recordings.c.id == id)
        result = await get_database().fetch_one(query)
        return Recording(**result) if result else None

    async def get_by_object_key(
        self, bucket_name: str, object_key: str
    ) -> Recording | None:
        query = recordings.select().where(
            recordings.c.bucket_name == bucket_name,
            recordings.c.object_key == object_key,
        )
        result = await get_database().fetch_one(query)
        return Recording(**result) if result else None

    async def remove_by_id(self, id: str) -> None:
        query = recordings.delete().where(recordings.c.id == id)
        await get_database().execute(query)

    async def get_by_ids(self, recording_ids: list[str]) -> list[Recording]:
        if not recording_ids:
            return []

        query = recordings.select().where(recordings.c.id.in_(recording_ids))
        results = await get_database().fetch_all(query)
        return [Recording(**row) for row in results]

    async def get_multitrack_needing_reprocessing(
        self, bucket_name: str
    ) -> list[Recording]:
        """
        Get multitrack recordings that need reprocessing:
        - Have track_keys (multitrack)
        - Either have no transcript OR transcript has error status

        This is more efficient than fetching all recordings and filtering in Python.
        """
        from reflector.db.transcripts import transcripts

        query = (
            recordings.select()
            .outerjoin(transcripts, recordings.c.id == transcripts.c.recording_id)
            .where(
                recordings.c.bucket_name == bucket_name,
                recordings.c.track_keys.isnot(None),
                or_(
                    transcripts.c.id.is_(None),
                    transcripts.c.status == "error",
                ),
            )
        )
        results = await get_database().fetch_all(query)
        recordings_list = [Recording(**row) for row in results]
        return [r for r in recordings_list if r.is_multitrack]


recordings_controller = RecordingController()
