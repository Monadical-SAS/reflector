"""add_daily_recording_requests

Revision ID: f5b008fa8a14
Revises: 1b1e6a6fc465
Create Date: 2026-01-20 22:32:06.697144

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5b008fa8a14"
down_revision: Union[str, None] = "1b1e6a6fc465"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_recording_request",
        sa.Column("recording_id", sa.String(), nullable=False),
        sa.Column("meeting_id", sa.String(), nullable=False),
        sa.Column("instance_id", sa.String(), nullable=False),
        sa.Column("type", sa.String(), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meeting.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("recording_id"),
    )
    op.create_index("idx_meeting_id", "daily_recording_request", ["meeting_id"])
    op.create_index("idx_instance_id", "daily_recording_request", ["instance_id"])

    # Clean up orphaned recordings before adding FK constraint
    op.execute("""
        UPDATE recording SET status = 'orphan', meeting_id = NULL
        WHERE meeting_id IS NOT NULL
        AND meeting_id NOT IN (SELECT id FROM meeting)
    """)

    # Add FK constraint to recording table (cascade delete recordings when meeting deleted)
    op.execute("""
        ALTER TABLE recording ADD CONSTRAINT fk_recording_meeting
          FOREIGN KEY (meeting_id) REFERENCES meeting(id) ON DELETE CASCADE
    """)

    # Add CHECK constraints to enforce orphan invariants
    op.execute("""
        ALTER TABLE recording ADD CONSTRAINT chk_orphan_no_meeting
          CHECK (status != 'orphan' OR meeting_id IS NULL)
    """)
    op.execute("""
        ALTER TABLE recording ADD CONSTRAINT chk_non_orphan_has_meeting
          CHECK (status = 'orphan' OR meeting_id IS NOT NULL)
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE recording DROP CONSTRAINT IF EXISTS chk_orphan_no_meeting")
    op.execute(
        "ALTER TABLE recording DROP CONSTRAINT IF EXISTS chk_non_orphan_has_meeting"
    )
    op.execute("ALTER TABLE recording DROP CONSTRAINT IF EXISTS fk_recording_meeting")
    op.drop_index("idx_instance_id", table_name="daily_recording_request")
    op.drop_index("idx_meeting_id", table_name="daily_recording_request")
    op.drop_table("daily_recording_request")
