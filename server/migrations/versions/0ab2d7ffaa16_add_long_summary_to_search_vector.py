"""add_long_summary_to_search_vector

Revision ID: 0ab2d7ffaa16
Revises: b1c33bd09963
Create Date: 2025-08-15 13:27:52.680211

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0ab2d7ffaa16"
down_revision: Union[str, None] = "b1c33bd09963"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the existing search vector column and index
    op.drop_index("idx_transcript_search_vector_en", table_name="transcript")
    op.drop_column("transcript", "search_vector_en")

    # Recreate the search vector column with long_summary included
    op.execute("""
        ALTER TABLE transcript ADD COLUMN search_vector_en tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(long_summary, '')), 'B') ||
            setweight(to_tsvector('english', coalesce(webvtt, '')), 'C')
        ) STORED
    """)

    # Recreate the GIN index for the search vector
    op.create_index(
        "idx_transcript_search_vector_en",
        "transcript",
        ["search_vector_en"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    # Drop the updated search vector column and index
    op.drop_index("idx_transcript_search_vector_en", table_name="transcript")
    op.drop_column("transcript", "search_vector_en")

    # Recreate the original search vector column without long_summary
    op.execute("""
        ALTER TABLE transcript ADD COLUMN search_vector_en tsvector
        GENERATED ALWAYS AS (
            setweight(to_tsvector('english', coalesce(title, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(webvtt, '')), 'B')
        ) STORED
    """)

    # Recreate the GIN index for the search vector
    op.create_index(
        "idx_transcript_search_vector_en",
        "transcript",
        ["search_vector_en"],
        postgresql_using="gin",
    )
