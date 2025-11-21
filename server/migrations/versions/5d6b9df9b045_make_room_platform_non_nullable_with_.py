"""Make room platform non-nullable with dynamic default

Revision ID: 5d6b9df9b045
Revises: 2b92a1b03caa
Create Date: 2025-11-21 13:22:25.756584

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5d6b9df9b045"
down_revision: Union[str, None] = "2b92a1b03caa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE room SET platform = 'whereby' WHERE platform IS NULL")

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.alter_column("platform", existing_type=sa.String(), nullable=False)


def downgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.alter_column("platform", existing_type=sa.String(), nullable=True)
