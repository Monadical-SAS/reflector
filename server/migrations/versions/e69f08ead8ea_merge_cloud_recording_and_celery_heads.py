"""merge cloud recording and celery heads

Revision ID: e69f08ead8ea
Revises: 1b1e6a6fc465, 80beb1ea3269
Create Date: 2026-01-21 21:39:10.326841

"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "e69f08ead8ea"
down_revision: Union[str, None] = ("1b1e6a6fc465", "80beb1ea3269")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
