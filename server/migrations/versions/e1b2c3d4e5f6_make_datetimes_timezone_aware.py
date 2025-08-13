"""make datetimes timezone aware

Revision ID: e1b2c3d4e5f6
Revises: b7df9609542c
Create Date: 2025-08-13 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1b2c3d4e5f6"
down_revision: Union[str, None] = "b7df9609542c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Meeting table: start_date, end_date
    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.alter_column(
            "start_date",
            type_=sa.TIMESTAMP(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "end_date",
            type_=sa.TIMESTAMP(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True,
        )

    # Room table: created_at
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            type_=sa.TIMESTAMP(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
        )

    # Transcript table: created_at
    with op.batch_alter_table("transcript", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            type_=sa.TIMESTAMP(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=True,
        )

    # Recording table: recorded_at
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.alter_column(
            "recorded_at",
            type_=sa.TIMESTAMP(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
        )

    # Meeting consent table: consent_timestamp
    with op.batch_alter_table("meeting_consent", schema=None) as batch_op:
        batch_op.alter_column(
            "consent_timestamp",
            type_=sa.TIMESTAMP(timezone=True),
            existing_type=sa.DateTime(),
            existing_nullable=False,
        )


def downgrade() -> None:
    # Revert Meeting table: start_date, end_date
    with op.batch_alter_table("meeting", schema=None) as batch_op:
        batch_op.alter_column(
            "start_date",
            type_=sa.DateTime(),
            existing_type=sa.TIMESTAMP(timezone=True),
            existing_nullable=True,
        )
        batch_op.alter_column(
            "end_date",
            type_=sa.DateTime(),
            existing_type=sa.TIMESTAMP(timezone=True),
            existing_nullable=True,
        )

    # Revert Room table: created_at
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            type_=sa.DateTime(),
            existing_type=sa.TIMESTAMP(timezone=True),
            existing_nullable=False,
        )

    # Revert Transcript table: created_at
    with op.batch_alter_table("transcript", schema=None) as batch_op:
        batch_op.alter_column(
            "created_at",
            type_=sa.DateTime(),
            existing_type=sa.TIMESTAMP(timezone=True),
            existing_nullable=True,
        )

    # Revert Recording table: recorded_at
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.alter_column(
            "recorded_at",
            type_=sa.DateTime(),
            existing_type=sa.TIMESTAMP(timezone=True),
            existing_nullable=False,
        )

    # Revert Meeting consent table: consent_timestamp
    with op.batch_alter_table("meeting_consent", schema=None) as batch_op:
        batch_op.alter_column(
            "consent_timestamp",
            type_=sa.DateTime(),
            existing_type=sa.TIMESTAMP(timezone=True),
            existing_nullable=False,
        )
