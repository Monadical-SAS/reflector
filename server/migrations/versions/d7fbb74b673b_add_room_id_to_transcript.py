"""Add room_id to transcript

Revision ID: d7fbb74b673b
Revises: a9c9c229ee36
Create Date: 2025-07-17 12:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7fbb74b673b"
down_revision: Union[str, None] = "a9c9c229ee36"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add room_id column to transcript table
    op.add_column("transcript", sa.Column("room_id", sa.String(), nullable=True))

    # Add index for room_id for better query performance
    op.create_index("idx_transcript_room_id", "transcript", ["room_id"])

    # Populate room_id for existing ROOM-type transcripts
    # This joins through recording -> meeting -> room to get the room_id
    op.execute("""
        UPDATE transcript AS t
        SET room_id = r.id
        FROM recording rec
        JOIN meeting m ON rec.meeting_id = m.id
        JOIN room r ON m.room_id = r.id
        WHERE t.recording_id = rec.id
        AND t.source_kind = 'room'
        AND t.room_id IS NULL
    """)

    # Fix missing meeting_id for ROOM-type transcripts
    # The meeting_id field exists but was never populated
    op.execute("""
        UPDATE transcript AS t
        SET meeting_id = rec.meeting_id
        FROM recording rec
        WHERE t.recording_id = rec.id
        AND t.source_kind = 'room'
        AND t.meeting_id IS NULL
        AND rec.meeting_id IS NOT NULL
    """)


def downgrade() -> None:
    # Drop the index first
    op.drop_index("idx_transcript_room_id", "transcript")

    # Drop the room_id column
    op.drop_column("transcript", "room_id")