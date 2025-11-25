"""add daily participant session table with immutable left_at

Revision ID: 2b92a1b03caa
Revises: f8294b31f022
Create Date: 2025-11-13 20:29:30.486577

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2b92a1b03caa"
down_revision: Union[str, None] = "f8294b31f022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create table
    op.create_table(
        "daily_participant_session",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("meeting_id", sa.String(), nullable=False),
        sa.Column("room_id", sa.String(), nullable=False),
        sa.Column("session_id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=True),
        sa.Column("user_name", sa.String(), nullable=False),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["meeting_id"], ["meeting.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["room_id"], ["room.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    with op.batch_alter_table("daily_participant_session", schema=None) as batch_op:
        batch_op.create_index(
            "idx_daily_session_meeting_left", ["meeting_id", "left_at"], unique=False
        )
        batch_op.create_index("idx_daily_session_room", ["room_id"], unique=False)

    # Create trigger function to prevent left_at from being updated once set
    op.execute("""
        CREATE OR REPLACE FUNCTION prevent_left_at_update()
        RETURNS TRIGGER AS $$
        BEGIN
            IF OLD.left_at IS NOT NULL THEN
                RAISE EXCEPTION 'left_at is immutable once set';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Create trigger
    op.execute("""
        CREATE TRIGGER prevent_left_at_update_trigger
        BEFORE UPDATE ON daily_participant_session
        FOR EACH ROW
        EXECUTE FUNCTION prevent_left_at_update();
    """)


def downgrade() -> None:
    # Drop trigger
    op.execute(
        "DROP TRIGGER IF EXISTS prevent_left_at_update_trigger ON daily_participant_session;"
    )

    # Drop trigger function
    op.execute("DROP FUNCTION IF EXISTS prevent_left_at_update();")

    # Drop indexes and table
    with op.batch_alter_table("daily_participant_session", schema=None) as batch_op:
        batch_op.drop_index("idx_daily_session_room")
        batch_op.drop_index("idx_daily_session_meeting_left")

    op.drop_table("daily_participant_session")
