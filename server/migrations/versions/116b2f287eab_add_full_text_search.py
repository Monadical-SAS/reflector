"""add_full_text_search

Revision ID: 116b2f287eab
Revises: 0bc0f3ff0111
Create Date: 2025-08-07 11:27:38.473517

"""

from typing import Sequence, Union

from alembic import op

revision: str = "116b2f287eab"
down_revision: Union[str, None] = "0bc0f3ff0111"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.execute("""
        ALTER TABLE transcript ADD COLUMN search_vector_en tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(webvtt, '')), 'B')
        ) STORED
    """)

    op.create_index(
        "idx_transcript_search_vector_en",
        "transcript",
        ["search_vector_en"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    conn = op.get_bind()
    if conn.dialect.name != "postgresql":
        return

    op.drop_index("idx_transcript_search_vector_en", table_name="transcript")
    op.drop_column("transcript", "search_vector_en")
