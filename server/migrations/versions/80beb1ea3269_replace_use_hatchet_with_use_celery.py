"""replace_use_hatchet_with_use_celery

Revision ID: 80beb1ea3269
Revises: bd3a729bb379
Create Date: 2026-01-20 16:26:25.555869

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "80beb1ea3269"
down_revision: Union[str, None] = "bd3a729bb379"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "use_celery",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            )
        )
        batch_op.drop_column("use_hatchet")


def downgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "use_hatchet",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            )
        )
        batch_op.drop_column("use_celery")
