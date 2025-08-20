"""add_grace_period_fields_to_meeting

Revision ID: d4a1c446458c
Revises: 6025e9b2bef2
Create Date: 2025-08-18 18:50:37.768052

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4a1c446458c"
down_revision: Union[str, None] = "6025e9b2bef2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add fields to track when participants left for grace period logic
    op.add_column(
        "meeting", sa.Column("last_participant_left_at", sa.DateTime(timezone=True))
    )
    op.add_column(
        "meeting",
        sa.Column("grace_period_minutes", sa.Integer, server_default=sa.text("15")),
    )


def downgrade() -> None:
    op.drop_column("meeting", "grace_period_minutes")
    op.drop_column("meeting", "last_participant_left_at")
