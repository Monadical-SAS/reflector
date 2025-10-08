"""add_platform_support

Revision ID: 1e49625677e4
Revises: dc035ff72fd5
Create Date: 2025-10-08 13:17:29.943612

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "1e49625677e4"
down_revision: Union[str, None] = "dc035ff72fd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add platform field with default 'whereby' for backward compatibility."""
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.String(),
                nullable=False,
                server_default="whereby",
            )
        )

    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "platform",
                sa.String(),
                nullable=False,
                server_default="whereby",
            )
        )


def downgrade() -> None:
    """Remove platform field."""
    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.drop_column("platform")

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("platform")
