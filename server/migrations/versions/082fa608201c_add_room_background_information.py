"""add_room_background_information

Revision ID: 082fa608201c
Revises: b7df9609542c
Create Date: 2025-07-29 01:41:37.912195

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '082fa608201c'
down_revision: Union[str, None] = 'b7df9609542c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('room', sa.Column('background_information', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('room', 'background_information')
