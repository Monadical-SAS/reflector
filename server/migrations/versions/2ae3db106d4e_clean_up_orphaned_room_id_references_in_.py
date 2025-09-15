"""clean up orphaned room_id references in meeting table

Revision ID: 2ae3db106d4e
Revises: def1b5867d4c
Create Date: 2025-09-11 10:35:15.759967

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2ae3db106d4e"
down_revision: Union[str, None] = "def1b5867d4c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Set room_id to NULL for meetings that reference non-existent rooms
    op.execute("""
        UPDATE meeting
        SET room_id = NULL
        WHERE room_id IS NOT NULL
          AND room_id NOT IN (SELECT id FROM room WHERE id IS NOT NULL)
    """)


def downgrade() -> None:
    # Cannot restore orphaned references - no operation needed
    pass
