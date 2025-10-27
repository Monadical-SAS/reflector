from typing import Annotated, Optional

import celery
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

import reflector.auth as auth
from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import transcripts_controller
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)

router = APIRouter()


class ProcessStatus(BaseModel):
    status: str


@router.post("/transcripts/{transcript_id}/process")
async def transcript_process(
    transcript_id: str,
    user: Annotated[Optional[auth.UserInfo], Depends(auth.current_user_optional)],
):
    user_id = user["sub"] if user else None
    transcript = await transcripts_controller.get_by_id_for_http(
        transcript_id, user_id=user_id
    )

    if transcript.locked:
        raise HTTPException(status_code=400, detail="Transcript is locked")

    if transcript.status == "idle":
        raise HTTPException(
            status_code=400, detail="Recording is not ready for processing"
        )

    # avoid duplicate scheduling for either pipeline
    if task_is_scheduled_or_active(
        "reflector.pipelines.main_file_pipeline.task_pipeline_file_process",
        transcript_id=transcript_id,
    ) or task_is_scheduled_or_active(
        "reflector.pipelines.main_multitrack_pipeline.task_pipeline_multitrack_process",
        transcript_id=transcript_id,
    ):
        return ProcessStatus(status="already running")

    # Determine processing mode strictly from DB to avoid S3 scans
    run_multitrack = False
    bucket_name = None
    track_keys: list[str] = []

    if transcript.recording_id:
        recording = await recordings_controller.get_by_id(transcript.recording_id)
        if recording:
            bucket_name = recording.bucket_name
            track_keys = list(getattr(recording, "track_keys", []) or [])
            run_multitrack = bool(track_keys)

    if run_multitrack and bucket_name and track_keys:
        task_pipeline_multitrack_process.delay(
            transcript_id=transcript_id,
            bucket_name=bucket_name,
            track_keys=track_keys,
        )
    else:
        # Default single-file pipeline
        task_pipeline_file_process.delay(transcript_id=transcript_id)

    return ProcessStatus(status="ok")


def task_is_scheduled_or_active(task_name: str, **kwargs):
    inspect = celery.current_app.control.inspect()

    for worker, tasks in (inspect.scheduled() | inspect.active()).items():
        for task in tasks:
            if task["name"] == task_name and task["kwargs"] == kwargs:
                return True

    return False
