"""add_change_seq_to_transcript

Revision ID: 623af934249a
Revises: 3aa20b96d963
Create Date: 2026-02-19 18:53:12.315440

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "623af934249a"
down_revision: Union[str, None] = "3aa20b96d963"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Sequence
    op.execute("CREATE SEQUENCE IF NOT EXISTS transcript_change_seq;")

    # Column (nullable first for backfill)
    op.add_column("transcript", sa.Column("change_seq", sa.BigInteger(), nullable=True))

    # Backfill existing rows with sequential values (ordered by created_at for determinism)
    op.execute("""
        UPDATE transcript SET change_seq = sub.seq FROM (
            SELECT id, nextval('transcript_change_seq') AS seq
            FROM transcript ORDER BY created_at ASC
        ) sub WHERE transcript.id = sub.id;
    """)

    # Now make NOT NULL
    op.alter_column("transcript", "change_seq", nullable=False)

    # Default for any inserts between now and trigger creation
    op.alter_column(
        "transcript",
        "change_seq",
        server_default=sa.text("nextval('transcript_change_seq')"),
    )

    # Trigger function
    op.execute("""
        CREATE OR REPLACE FUNCTION set_transcript_change_seq()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.change_seq := nextval('transcript_change_seq');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Trigger (fires on every INSERT or UPDATE)
    op.execute("""
        CREATE TRIGGER trigger_transcript_change_seq
            BEFORE INSERT OR UPDATE ON transcript
            FOR EACH ROW
            EXECUTE FUNCTION set_transcript_change_seq();
    """)

    # Index for efficient polling
    op.create_index("idx_transcript_change_seq", "transcript", ["change_seq"])


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trigger_transcript_change_seq ON transcript;")
    op.execute("DROP FUNCTION IF EXISTS set_transcript_change_seq();")
    op.drop_index("idx_transcript_change_seq", table_name="transcript")
    op.drop_column("transcript", "change_seq")
    op.execute("DROP SEQUENCE IF EXISTS transcript_change_seq;")
