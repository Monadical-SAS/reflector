"""add_unique_constraint_one_active_meeting_per_room

Revision ID: b7df9609542c
Revises: d7fbb74b673b
Create Date: 2025-07-25 16:27:06.959868

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7df9609542c'
down_revision: Union[str, None] = 'd7fbb74b673b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create a partial unique index that ensures only one active meeting per room
    # This works for both PostgreSQL and SQLite
    op.create_index(
        'idx_one_active_meeting_per_room',
        'meeting',
        ['room_id'],
        unique=True,
        postgresql_where=sa.text('is_active = true'),
        sqlite_where=sa.text('is_active = 1')
    )


def downgrade() -> None:
    op.drop_index('idx_one_active_meeting_per_room', table_name='meeting')
