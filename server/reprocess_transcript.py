#!/usr/bin/env python
"""
Reprocess the Daily.co multitrack recording to fix audio mixdown
"""

import asyncio

from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)


async def reprocess():
    """Process the multitrack recording with fixed mixdown"""

    bucket_name = "reflector-dailyco-local"
    track_keys = [
        "monadical/daily-20251020193458/1760988935484-52f7f48b-fbab-431f-9a50-87b9abfc8255-cam-audio-1760988935922",
        "monadical/daily-20251020193458/1760988935484-a37c35e3-6f8e-4274-a482-e9d0f102a732-cam-audio-1760988943823",
    ]

    # Create a new transcript with fixed mixdown
    import uuid

    from reflector.db import get_database
    from reflector.db.transcripts import Transcript, transcripts

    db = get_database()
    await db.connect()

    try:
        transcript_id = str(uuid.uuid4())
        transcript = Transcript(
            id=transcript_id,
            name="Daily Multitrack - With Audio Mixdown",
            source_kind="file",
            source_language="en",
            target_language="en",
            status="idle",
            events=[],
            title="",
        )

        query = transcripts.insert().values(**transcript.model_dump())
        await db.execute(query)
        print(f"Created transcript: {transcript_id}")

        # Process with the fixed pipeline
        await task_pipeline_multitrack_process(
            transcript_id=transcript_id, bucket_name=bucket_name, track_keys=track_keys
        )

        print(
            f"Processing complete! Check: http://localhost:3000/transcripts/{transcript_id}"
        )

        return transcript_id
    finally:
        await db.disconnect()


if __name__ == "__main__":
    transcript_id = asyncio.run(reprocess())
    print(f"\n✅ Reprocessing complete!")
    print(f"📍 View at: http://localhost:3000/transcripts/{transcript_id}")
