"""add_webvtt_field_to_transcript

Revision ID: 0bc0f3ff0111
Revises: b7df9609542c
Create Date: 2025-08-05 19:36:41.740957

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0bc0f3ff0111'
down_revision: Union[str, None] = 'b7df9609542c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add webvtt column to transcript table
    op.add_column('transcript', 
        sa.Column('webvtt', sa.Text(), nullable=True)
    )


def downgrade() -> None:
    # Remove webvtt column from transcript table
    op.drop_column('transcript', 'webvtt')
