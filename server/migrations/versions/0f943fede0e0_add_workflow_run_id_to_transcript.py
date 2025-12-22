"""add workflow_run_id to transcript

Revision ID: 0f943fede0e0
Revises: 20251217000000
Create Date: 2025-12-16 01:54:13.855106

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0f943fede0e0"
down_revision: Union[str, None] = "20251217000000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("transcript", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workflow_run_id", sa.String(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("transcript", schema=None) as batch_op:
        batch_op.drop_column("workflow_run_id")
