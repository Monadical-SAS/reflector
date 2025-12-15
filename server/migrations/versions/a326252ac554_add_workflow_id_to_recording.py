"""add workflow_id to recording

Revision ID: a326252ac554
Revises: bbafedfa510c
Create Date: 2025-12-14 11:34:22.137910

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a326252ac554"
down_revision: Union[str, None] = "bbafedfa510c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.add_column(sa.Column("workflow_id", sa.String(), nullable=True))
        batch_op.create_index(
            "idx_recording_workflow_id", ["workflow_id"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("recording", schema=None) as batch_op:
        batch_op.drop_index("idx_recording_workflow_id")
        batch_op.drop_column("workflow_id")
