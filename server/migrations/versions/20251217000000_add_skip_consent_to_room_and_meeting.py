"""add skip_consent to room and meeting

Revision ID: 20251217000000
Revises: 05f8688d6895
Create Date: 2025-12-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20251217000000"
down_revision: Union[str, None] = "05f8688d6895"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "skip_consent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )

    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "skip_consent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.drop_column("skip_consent")

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("skip_consent")
