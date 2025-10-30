"""add daily platform and user api keys

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
    """Add platform support for Daily.co and user API keys."""
    # Add platform field to room and meeting tables
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

    # Add track_keys for multitrack recordings
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.add_column(sa.Column("track_keys", sa.JSON(), nullable=True))

    # Create user_api_key table
    op.create_table(
        "user_api_key",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    with op.batch_alter_table("user_api_key", schema=None) as batch_op:
        batch_op.create_index("idx_user_api_key_hash", ["key_hash"], unique=True)
        batch_op.create_index("idx_user_api_key_user_id", ["user_id"], unique=False)


def downgrade() -> None:
    """Remove Daily.co platform support and user API keys."""
    op.drop_table("user_api_key")

    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.drop_column("track_keys")

    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.drop_column("platform")

    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("platform")
