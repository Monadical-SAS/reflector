"""add_track_keys

Revision ID: f8294b31f022
Revises: 1e49625677e4
Create Date: 2025-10-27 18:52:17.589167

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8294b31f022"
down_revision: Union[str, None] = "1e49625677e4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.add_column(sa.Column("track_keys", sa.JSON(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.drop_column("track_keys")
