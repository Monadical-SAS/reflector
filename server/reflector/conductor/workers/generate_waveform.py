"""Conductor worker: generate_waveform - Generate waveform visualization data."""

import tempfile
from pathlib import Path

import httpx

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger
from reflector.storage import get_transcripts_storage
from reflector.utils.audio_waveform import get_audio_waveform

PRESIGNED_URL_EXPIRATION_SECONDS = 7200


@worker_task(task_definition_name="generate_waveform")
def generate_waveform(task: Task) -> TaskResult:
    """Generate waveform visualization data from mixed audio.

    Input:
        audio_key: str - S3 key of the audio file
        transcript_id: str - Transcript ID

    Output:
        waveform: list[float] - Waveform peaks array
    """
    audio_key = task.input_data.get("audio_key")
    transcript_id = task.input_data.get("transcript_id")

    logger.info(
        "[Worker] generate_waveform", audio_key=audio_key, transcript_id=transcript_id
    )

    if transcript_id:
        emit_progress(
            transcript_id, "generate_waveform", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not audio_key or not transcript_id:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing audio_key or transcript_id"
        return task_result

    import asyncio

    async def _process():
        storage = get_transcripts_storage()
        audio_url = await storage.get_file_url(
            audio_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
        )

        # Download audio to temp file
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = Path(tmp.name)
            async with httpx.AsyncClient() as client:
                resp = await client.get(audio_url)
                resp.raise_for_status()
                tmp.write(resp.content)

        try:
            waveform = get_audio_waveform(tmp_path, segments_count=255)
        finally:
            tmp_path.unlink(missing_ok=True)

        return waveform

    try:
        waveform = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"waveform": waveform}

        logger.info(
            "[Worker] generate_waveform complete",
            transcript_id=transcript_id,
            peaks_count=len(waveform) if waveform else 0,
        )

        if transcript_id:
            emit_progress(
                transcript_id,
                "generate_waveform",
                "completed",
                task.workflow_instance_id,
            )

    except Exception as e:
        logger.error("[Worker] generate_waveform failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "generate_waveform", "failed", task.workflow_instance_id
            )

    return task_result
