"""Add recordings

Revision ID: d3ff3a39297f
Revises: b0e5f7876032
Create Date: 2025-03-10 14:38:53.504413

"""

import uuid
from datetime import datetime
from typing import Sequence, Union

import boto3
import sqlalchemy as sa
from alembic import op
from reflector.db.meetings import meetings
from reflector.db.recordings import Recording, recordings
from reflector.db.transcripts import transcripts
from reflector.settings import settings

# revision identifiers, used by Alembic.
revision: str = "d3ff3a39297f"
down_revision: Union[str, None] = "b0e5f7876032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def add_recordings_from_s3():
    bind = op.get_bind()

    s3 = boto3.client(
        "s3",
        region_name=settings.TRANSCRIPT_STORAGE_AWS_REGION,
        aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
    )

    bucket_name = settings.AWS_WHEREBY_S3_BUCKET
    paginator = s3.get_paginator("list_objects_v2")
    pages = paginator.paginate(Bucket=bucket_name)

    for page in pages:
        if "Contents" not in page:
            continue

        for obj in page["Contents"]:
            object_key = obj["Key"]

            if not (object_key.endswith(".mp4")):
                continue

            room_name = f"/{object_key[:36]}"
            recorded_at = datetime.fromisoformat(object_key[37:57])

            meeting = bind.execute(
                meetings.select().where(meetings.c.room_name == room_name)
            ).fetchone()

            recording = Recording(
                id=str(uuid.uuid4()),
                bucket_name=bucket_name,
                object_key=object_key,
                recorded_at=recorded_at,
                meeting_id=meeting["id"],
            )
            bind.execute(recordings.insert().values(recording.model_dump()))


def link_transcripts_to_recordings():
    bind = op.get_bind()

    room_transcripts = bind.execute(
        transcripts.select()
        .where(transcripts.c.meeting_id.isnot(None))
        .order_by(transcripts.c.meeting_id, transcripts.c.created_at)
    ).fetchall()

    for transcript in room_transcripts:
        transcript_recordings = bind.execute(
            recordings.select()
            .where(
                recordings.c.meeting_id == transcript["meeting_id"],
            )
            .order_by(recordings.c.recorded_at.desc())
        ).fetchall()

        if len(transcript_recordings) == 1:
            bind.execute(
                transcripts.update()
                .where(transcripts.c.id == transcript["id"])
                .values(recording_id=transcript_recordings[0]["id"])
            )
        elif len(transcript_recordings) > 1:
            matched_recording = next(
                (
                    r
                    for r in transcript_recordings
                    if r["recorded_at"] <= transcript["created_at"]
                ),
                None,
            )
            bind.execute(
                transcripts.update()
                .where(transcripts.c.id == transcript["id"])
                .values(recording_id=matched_recording["id"])
            )


def delete_recordings():
    bind = op.get_bind()
    bind.execute(recordings.delete())


def upgrade() -> None:
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.create_unique_constraint(
            "uq_recording_object_key",
            ["bucket_name", "object_key"],
        )
    op.add_column("transcript", sa.Column("recording_id", sa.String(), nullable=True))

    add_recordings_from_s3()
    link_transcripts_to_recordings()


def downgrade() -> None:
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.drop_constraint("uq_recording_object_key", type_="unique")
    op.drop_column("transcript", "recording_id")

    delete_recordings()
