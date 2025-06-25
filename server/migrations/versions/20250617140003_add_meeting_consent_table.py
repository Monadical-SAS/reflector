"""add meeting consent table

Revision ID: 20250617140003
Revises: f819277e5169
Create Date: 2025-06-17 14:00:03.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250617140003"
down_revision: Union[str, None] = "d3ff3a39297f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'meeting_consent',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('meeting_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('consent_given', sa.Boolean(), nullable=False),
        sa.Column('consent_timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['meeting_id'], ['meeting.id']),
    )


def downgrade() -> None:
    op.drop_table('meeting_consent')