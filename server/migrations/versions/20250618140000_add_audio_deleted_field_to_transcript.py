"""add audio_deleted field to transcript

Revision ID: 20250618140000
Revises: 20250617140003
Create Date: 2025-06-18 14:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250618140000"
down_revision: Union[str, None] = "20250617140003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transcript", sa.Column("audio_deleted", sa.Boolean(), nullable=True))


def downgrade() -> None:
    op.drop_column("transcript", "audio_deleted")