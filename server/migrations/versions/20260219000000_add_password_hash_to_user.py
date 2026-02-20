"""add password_hash to user table

Revision ID: 20260219000000
Revises: 3aa20b96d963
Create Date: 2026-02-19 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260219000000"
down_revision: Union[str, None] = "3aa20b96d963"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("password_hash", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("user", "password_hash")
