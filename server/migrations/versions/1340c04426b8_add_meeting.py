"""add meeting

Revision ID: 1340c04426b8
Revises: b9348748bbbc
Create Date: 2024-07-31 16:41:29.415218

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1340c04426b8"
down_revision: Union[str, None] = "b9348748bbbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transcript", sa.Column("meeting_id", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("transcript", "meeting_id")
