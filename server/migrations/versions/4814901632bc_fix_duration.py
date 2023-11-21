"""fix duration

Revision ID: 4814901632bc
Revises: 38a927dcb099
Create Date: 2023-11-10 18:12:17.886522

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import select


# revision identifiers, used by Alembic.
revision: str = "4814901632bc"
down_revision: Union[str, None] = "38a927dcb099"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # for all the transcripts, calculate the duration from the mp3
    # and update the duration column
    from pathlib import Path
    from reflector.settings import settings
    import av

    bind = op.get_bind()
    transcript = table(
        "transcript", column("id", sa.String), column("duration", sa.Float)
    )

    # select only the one with duration = 0
    results = bind.execute(
        select([transcript.c.id, transcript.c.duration]).where(
            transcript.c.duration == 0
        )
    )

    data_dir = Path(settings.DATA_DIR)
    for row in results:
        audio_path = data_dir / row["id"] / "audio.mp3"
        if not audio_path.exists():
            continue

        try:
            print(f"Processing {audio_path}")
            container = av.open(audio_path.as_posix())
            print(container.duration)
            duration = round(float(container.duration / av.time_base), 2)
            print(f"Duration: {duration}")
            bind.execute(
                transcript.update()
                .where(transcript.c.id == row["id"])
                .values(duration=duration)
            )
        except Exception as e:
            print(f"Failed to process {audio_path}: {e}")


def downgrade() -> None:
    pass
