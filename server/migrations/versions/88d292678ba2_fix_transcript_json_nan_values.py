"""fix_transcript_json_nan_values

Revision ID: 88d292678ba2
Revises: 2cf0b60a9d34
Create Date: 2025-07-15 19:30:19.876332

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "88d292678ba2"
down_revision: Union[str, None] = "2cf0b60a9d34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    import json
    import re
    from sqlalchemy import text

    # Get database connection
    conn = op.get_bind()

    # Fetch all transcript records with events data
    result = conn.execute(
        text("SELECT id, events FROM transcript WHERE events IS NOT NULL")
    )

    def fix_nan(obj):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if isinstance(value, (dict, list)):
                    fix_nan(value)
                elif isinstance(value, float) and value != value:
                    obj[key] = None
        elif isinstance(obj, list):
            for i in range(len(obj)):
                if isinstance(obj[i], (dict, list)):
                    fix_nan(obj[i])
                elif isinstance(obj[i], float) and obj[i] != obj[i]:
                    obj[i] = None

    for transcript_id, events in result:
        if not events:
            continue
        if "NaN" not in events:
            continue

        try:
            jevents = json.loads(events)
            fix_nan(jevents)
            fixed_events = json.dumps(jevents)
            assert "NaN" not in fixed_events
        except (json.JSONDecodeError, AssertionError) as e:
            print(f"Warning: Invalid JSON for transcript {transcript_id}, skipping: {e}")
            continue

        # Update the record with fixed JSON
        conn.execute(
            text("UPDATE transcript SET events = :events WHERE id = :id"),
            {"events": fixed_events, "id": transcript_id},
        )


def downgrade() -> None:
    # No downgrade needed - this is a data fix
    pass
