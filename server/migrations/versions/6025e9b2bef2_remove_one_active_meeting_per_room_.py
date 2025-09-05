"""remove_one_active_meeting_per_room_constraint

Revision ID: 6025e9b2bef2
Revises: 61882a919591
Create Date: 2025-08-18 18:45:44.418392

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6025e9b2bef2"
down_revision: Union[str, None] = "61882a919591"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove the unique constraint that prevents multiple active meetings per room
    # This is needed to support calendar integration with overlapping meetings
    # Check if index exists before trying to drop it
    from alembic import context

    if context.get_context().dialect.name == "postgresql":
        conn = op.get_bind()
        result = conn.execute(
            sa.text(
                "SELECT 1 FROM pg_indexes WHERE indexname = 'idx_one_active_meeting_per_room'"
            )
        )
        if result.fetchone():
            op.drop_index("idx_one_active_meeting_per_room", table_name="meeting")
    else:
        # For SQLite, just try to drop it
        try:
            op.drop_index("idx_one_active_meeting_per_room", table_name="meeting")
        except:
            pass


def downgrade() -> None:
    # Restore the unique constraint
    op.create_index(
        "idx_one_active_meeting_per_room",
        "meeting",
        ["room_id"],
        unique=True,
        postgresql_where=sa.text("is_active = true"),
        sqlite_where=sa.text("is_active = 1"),
    )
