"""add user table

Revision ID: bbafedfa510c
Revises: 5d6b9df9b045
Create Date: 2025-11-19 21:06:30.543262

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "bbafedfa510c"
down_revision: Union[str, None] = "5d6b9df9b045"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "user",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("uid", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("user", schema=None) as batch_op:
        batch_op.create_index("idx_user_uid", ["uid"], unique=True)
        batch_op.create_index("idx_user_email", ["email"], unique=False)


def downgrade() -> None:
    op.drop_table("user")
