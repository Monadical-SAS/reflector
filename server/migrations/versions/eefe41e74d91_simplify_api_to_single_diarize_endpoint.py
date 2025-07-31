"""simplify_api_to_single_diarize_endpoint

Revision ID: eefe41e74d91
Revises: d7aff6c56c5d
Create Date: 2025-07-31 13:37:42.176303

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eefe41e74d91'
down_revision: Union[str, None] = 'd7aff6c56c5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Clean the jobs table completely (user allowed table cleaning)
    op.execute("DELETE FROM jobs")
    
    # The JobType enum will be updated in code to only include DIARIZATION
    # No database schema changes needed as job type is stored as string


def downgrade() -> None:
    # Cannot restore deleted jobs data
    # JobType enum changes will be reverted in code
    pass
