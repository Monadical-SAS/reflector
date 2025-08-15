"""add_search_optimization_indexes

Revision ID: b1c33bd09963
Revises: 9f5c78d352d6
Create Date: 2025-08-14 17:26:02.117408

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c33bd09963"
down_revision: Union[str, None] = "9f5c78d352d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add composite indexes for search filtering optimization
    # These indexes improve performance when filtering by multiple columns

    # Index for source_kind + status filtering (common combination)
    op.create_index(
        "idx_transcript_source_kind_status",
        "transcript",
        ["source_kind", "status"],
        if_not_exists=True,
    )

    # Index for status + created_at (for filtering by status with date ranges)
    op.create_index(
        "idx_transcript_status_created_at",
        "transcript",
        ["status", "created_at"],
        if_not_exists=True,
    )

    # Index for room_id + created_at (for room-specific searches with date ordering)
    op.create_index(
        "idx_transcript_room_id_created_at",
        "transcript",
        ["room_id", "created_at"],
        if_not_exists=True,
    )

    # Index for source_kind alone (if not already exists from single column usage)
    op.create_index(
        "idx_transcript_source_kind", "transcript", ["source_kind"], if_not_exists=True
    )

    # Index for status alone (frequently filtered field)
    op.create_index(
        "idx_transcript_status", "transcript", ["status"], if_not_exists=True
    )


def downgrade() -> None:
    # Remove the indexes in reverse order
    op.drop_index("idx_transcript_status", "transcript", if_exists=True)
    op.drop_index("idx_transcript_source_kind", "transcript", if_exists=True)
    op.drop_index("idx_transcript_room_id_created_at", "transcript", if_exists=True)
    op.drop_index("idx_transcript_status_created_at", "transcript", if_exists=True)
    op.drop_index("idx_transcript_source_kind_status", "transcript", if_exists=True)
