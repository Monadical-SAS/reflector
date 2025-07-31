"""Migration transcript to text field in transcripts table

Revision ID: 9920ecfe2735
Revises: 99365b0cd87b
Create Date: 2023-11-02 18:55:17.019498

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import select
from sqlalchemy.sql import column, table

# revision identifiers, used by Alembic.
revision: str = "9920ecfe2735"
down_revision: Union[str, None] = "99365b0cd87b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # bind the engine
    bind = op.get_bind()

    # Reflect the table
    transcript = table("transcript", column("id", sa.String), column("topics", sa.JSON))

    # Select all rows from the transcript table
    results = bind.execute(select([transcript.c.id, transcript.c.topics]))

    for row in results:
        transcript_id = row["id"]
        topics_json = row["topics"]

        # Process each topic in the topics JSON array
        updated_topics = []
        for topic in topics_json:
            if "transcript" in topic:
                # Rename key 'transcript' to 'text'
                topic["text"] = topic.pop("transcript")
            updated_topics.append(topic)

        # Update the transcript table
        bind.execute(
            transcript.update()
            .where(transcript.c.id == transcript_id)
            .values(topics=updated_topics)
        )


def downgrade() -> None:
    # bind the engine
    bind = op.get_bind()

    # Reflect the table
    transcript = table("transcript", column("id", sa.String), column("topics", sa.JSON))

    # Select all rows from the transcript table
    results = bind.execute(select([transcript.c.id, transcript.c.topics]))

    for row in results:
        transcript_id = row["id"]
        topics_json = row["topics"]

        # Process each topic in the topics JSON array
        updated_topics = []
        for topic in topics_json:
            if "text" in topic:
                # Rename key 'text' back to 'transcript'
                topic["transcript"] = topic.pop("text")
            updated_topics.append(topic)

        # Update the transcript table
        bind.execute(
            transcript.update()
            .where(transcript.c.id == transcript_id)
            .values(topics=updated_topics)
        )
