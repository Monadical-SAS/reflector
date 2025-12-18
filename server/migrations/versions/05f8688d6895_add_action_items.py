"""add_action_items

Revision ID: 05f8688d6895
Revises: bbafedfa510c
Create Date: 2025-12-12 11:57:50.209658

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "05f8688d6895"
down_revision: Union[str, None] = "bbafedfa510c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("transcript", sa.Column("action_items", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("transcript", "action_items")
