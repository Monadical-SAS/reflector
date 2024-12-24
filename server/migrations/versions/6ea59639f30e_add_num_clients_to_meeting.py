"""add num_clients to meeting

Revision ID: 6ea59639f30e
Revises: b469348df210
Create Date: 2024-12-24 10:50:03.109729

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6ea59639f30e"
down_revision: Union[str, None] = "b469348df210"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meeting",
        sa.Column(
            "num_clients", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
    )


def downgrade() -> None:
    op.drop_column("meeting", "num_clients")
