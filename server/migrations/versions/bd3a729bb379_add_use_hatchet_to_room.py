"""add use_hatchet to room

Revision ID: bd3a729bb379
Revises: 0f943fede0e0
Create Date: 2025-12-16 16:34:03.594231

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bd3a729bb379"
down_revision: Union[str, None] = "0f943fede0e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "use_hatchet",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("use_hatchet")
