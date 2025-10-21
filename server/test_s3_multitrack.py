#!/usr/bin/env python
"""
Test multitrack processing with correct S3 bucket configuration
"""

import asyncio
import uuid

from reflector.db import get_database
from reflector.db.transcripts import Transcript, transcripts
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)


async def create_and_process():
    """Create a new transcript and process with correct S3 bucket"""

    # Correct S3 configuration
    bucket_name = "reflector-dailyco-local"
    track_keys = [
        "monadical/daily-20251020193458/1760988935484-52f7f48b-fbab-431f-9a50-87b9abfc8255-cam-audio-1760988935922",
        "monadical/daily-20251020193458/1760988935484-a37c35e3-6f8e-4274-a482-e9d0f102a732-cam-audio-1760988943823",
    ]

    # Create a new transcript
    db = get_database()
    await db.connect()

    try:
        transcript_id = str(uuid.uuid4())
        transcript = Transcript(
            id=transcript_id,
            name="Daily Multitrack - Correct S3 Bucket Test",
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

        # Trigger processing with Celery
        result = task_pipeline_multitrack_process.delay(
            transcript_id=transcript_id, bucket_name=bucket_name, track_keys=track_keys
        )

        print(f"Task ID: {result.id}")
        print(
            f"Processing started! Check: http://localhost:3000/transcripts/{transcript_id}"
        )
        print(f"API Status: http://localhost:1250/v1/transcripts/{transcript_id}")

        return transcript_id
    finally:
        await db.disconnect()


if __name__ == "__main__":
    transcript_id = asyncio.run(create_and_process())
    print(f"\n✅ Task submitted successfully!")
    print(f"📍 Transcript ID: {transcript_id}")
