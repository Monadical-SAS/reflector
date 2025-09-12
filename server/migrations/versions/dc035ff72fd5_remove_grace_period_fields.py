"""remove_grace_period_fields

Revision ID: dc035ff72fd5
Revises: d8e204bbf615
Create Date: 2025-09-11 10:36:45.197588

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dc035ff72fd5"
down_revision: Union[str, None] = "d8e204bbf615"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove grace period columns from meeting table
    op.drop_column("meeting", "last_participant_left_at")
    op.drop_column("meeting", "grace_period_minutes")


def downgrade() -> None:
    # Add back grace period columns to meeting table
    op.add_column(
        "meeting",
        sa.Column(
            "last_participant_left_at", sa.DateTime(timezone=True), nullable=True
        ),
    )
    op.add_column(
        "meeting",
        sa.Column(
            "grace_period_minutes",
            sa.Integer(),
            server_default=sa.text("15"),
            nullable=True,
        ),
    )
