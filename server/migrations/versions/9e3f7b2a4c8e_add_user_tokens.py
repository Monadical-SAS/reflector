"""add user tokens

Revision ID: 9e3f7b2a4c8e
Revises: dc035ff72fd5
Create Date: 2025-10-17 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9e3f7b2a4c8e"
down_revision: Union[str, None] = "dc035ff72fd5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user_token",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("user_token", schema=None) as batch_op:
        batch_op.create_index("idx_user_token_hash", ["token_hash"], unique=True)
        batch_op.create_index("idx_user_token_user_id", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_table("user_token")
