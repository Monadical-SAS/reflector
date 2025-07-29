"""remove_user_id_from_jobs_table

Revision ID: d7aff6c56c5d
Revises: ddb285cb7cda
Create Date: 2025-07-29 20:56:18.593853

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7aff6c56c5d'
down_revision: Union[str, None] = 'ddb285cb7cda'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Remove user_id column from jobs table
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_jobs_user_id'))
        batch_op.drop_column('user_id')


def downgrade() -> None:
    # Add user_id column back to jobs table
    with op.batch_alter_table('jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.String(length=100), nullable=True))
        batch_op.create_index(batch_op.f('ix_jobs_user_id'), ['user_id'], unique=False)
