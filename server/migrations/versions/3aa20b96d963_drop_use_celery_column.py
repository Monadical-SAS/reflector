"""drop_use_celery_column

Revision ID: 3aa20b96d963
Revises: e69f08ead8ea
Create Date: 2026-02-05 10:12:44.065279

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "3aa20b96d963"
down_revision: Union[str, None] = "e69f08ead8ea"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.drop_column("use_celery")


def downgrade() -> None:
    with op.batch_alter_table("room", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "use_celery",
                sa.Boolean(),
                server_default=sa.text("false"),
                nullable=False,
            )
        )
