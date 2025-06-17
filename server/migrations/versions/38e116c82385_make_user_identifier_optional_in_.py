"""make user_identifier optional in meeting_consent

Revision ID: 38e116c82385
Revises: 20250617140003
Create Date: 2025-06-17 15:23:41.346980

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '38e116c82385'
down_revision: Union[str, None] = '20250617140003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Make user_identifier column nullable
    op.alter_column('meeting_consent', 'user_identifier',
                    existing_type=sa.String(),
                    nullable=True)


def downgrade() -> None:
    # Revert user_identifier back to non-nullable
    op.alter_column('meeting_consent', 'user_identifier',
                    existing_type=sa.String(),
                    nullable=False)
