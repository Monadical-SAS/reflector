#!/usr/bin/env python
"""
Trigger reprocessing of Daily.co multitrack recording via Celery
"""

from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)

# Trigger the Celery task
result = task_pipeline_multitrack_process.delay(
    transcript_id="32fad706-f8cf-434c-94c8-1ee69f7be081",  # The ID that was created
    bucket_name="reflector-dailyco-local",
    track_keys=[
        "monadical/daily-20251020193458/1760988935484-52f7f48b-fbab-431f-9a50-87b9abfc8255-cam-audio-1760988935922",
        "monadical/daily-20251020193458/1760988935484-a37c35e3-6f8e-4274-a482-e9d0f102a732-cam-audio-1760988943823",
    ],
)

print(f"Task ID: {result.id}")
print(
    f"Processing started! Check: http://localhost:3000/transcripts/32fad706-f8cf-434c-94c8-1ee69f7be081"
)
