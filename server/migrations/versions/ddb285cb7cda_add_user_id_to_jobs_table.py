"""Add user_id to jobs table

Revision ID: ddb285cb7cda
Revises: 31a75043472e
Create Date: 2025-07-29 12:19:04.348240

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ddb285cb7cda'
down_revision: Union[str, None] = '31a75043472e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add user_id column to jobs table
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_jobs_user_id'), ['user_id'], unique=False)


def downgrade() -> None:
    # Remove user_id column from jobs table
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_user_id'))
        batch_op.drop_column('user_id')
