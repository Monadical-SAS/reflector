"""add platform support

Revision ID: 20250801180012
Revises: b0e5f7876032
Create Date: 2025-08-01 18:00:12.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20250801180012"
down_revision: Union[str, None] = "b0e5f7876032"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add platform column to rooms table
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("platform", sa.String(), server_default="whereby", nullable=False)
        )

    # Add platform column to meeting table
    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("platform", sa.String(), server_default="whereby", nullable=False)
        )


def downgrade() -> None:
    # Remove platform columns
    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.drop_column("platform")

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("platform")
