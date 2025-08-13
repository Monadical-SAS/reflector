"""populate_webvtt_from_topics

Revision ID: 8120ebc75366
Revises: 116b2f287eab
Create Date: 2025-08-11 19:11:01.316947

"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '8120ebc75366'
down_revision: Union[str, None] = '116b2f287eab'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def topics_to_webvtt(topics):
    """Convert topics list to WebVTT format string."""
    if not topics:
        return None

    lines = ["WEBVTT", ""]

    for topic in topics:
        start_time = format_timestamp(topic.get("start"))
        end_time = format_timestamp(topic.get("end"))
        text = topic.get("text", "").strip()

        if start_time and end_time and text:
            lines.append(f"{start_time} --> {end_time}")
            lines.append(text)
            lines.append("")

    return "\n".join(lines).strip()


def format_timestamp(seconds):
    """Format seconds to WebVTT timestamp format (HH:MM:SS.mmm)."""
    if seconds is None:
        return None

    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60

    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"


def upgrade() -> None:
    """Populate WebVTT field for all transcripts with topics."""

    # Get connection
    connection = op.get_bind()

    # Query all transcripts with topics
    result = connection.execute(
        text("SELECT id, topics FROM transcript WHERE topics IS NOT NULL")
    )

    rows = result.fetchall()
    print(f"Found {len(rows)} transcripts with topics")

    updated_count = 0
    error_count = 0

    for row in rows:
        transcript_id = row[0]
        topics_data = row[1]

        if not topics_data:
            continue

        try:
            # Parse JSON if it's a string
            if isinstance(topics_data, str):
                topics_data = json.loads(topics_data)

            # Convert topics to WebVTT format
            webvtt_content = topics_to_webvtt(topics_data)

            if webvtt_content:
                # Update the webvtt field
                connection.execute(
                    text("UPDATE transcript SET webvtt = :webvtt WHERE id = :id"),
                    {"webvtt": webvtt_content, "id": transcript_id}
                )
                updated_count += 1
                print(f"✓ Updated transcript {transcript_id}")

        except Exception as e:
            error_count += 1
            print(f"✗ Error updating transcript {transcript_id}: {e}")

    print(f"\nMigration complete!")
    print(f"  Updated: {updated_count}")
    print(f"  Errors: {error_count}")


def downgrade() -> None:
    """Clear WebVTT field for all transcripts."""
    op.execute(
        text("UPDATE transcript SET webvtt = NULL")
    )
