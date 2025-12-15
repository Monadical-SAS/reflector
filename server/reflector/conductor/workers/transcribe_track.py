"""Conductor worker: transcribe_track - Transcribe audio track using GPU service."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="transcribe_track")
def transcribe_track(task: Task) -> TaskResult:
    """Transcribe audio track using GPU (Modal.com) or local Whisper.

    Input:
        track_index: int - Index of the track
        audio_url: str - Presigned URL of the audio file
        language: str - Language code (default: "en")
        transcript_id: str - Transcript ID for progress tracking

    Output:
        words: list[dict] - List of transcribed words with timestamps and speaker
        track_index: int - Track index (echoed back)
    """
    track_index = task.input_data.get("track_index", 0)
    audio_url = task.input_data.get("audio_url")
    language = task.input_data.get("language", "en")
    transcript_id = task.input_data.get("transcript_id")

    logger.info("[Worker] transcribe_track", track_index=track_index, language=language)

    if transcript_id:
        emit_progress(
            transcript_id, "transcribe_track", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not audio_url:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing audio_url"
        return task_result

    import asyncio

    async def _process():
        from reflector.pipelines.transcription_helpers import (
            transcribe_file_with_processor,
        )

        transcript = await transcribe_file_with_processor(audio_url, language)

        # Tag all words with speaker index
        words = []
        for word in transcript.words:
            word_dict = word.model_dump()
            word_dict["speaker"] = track_index
            words.append(word_dict)

        return words

    try:
        words = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "words": words,
            "track_index": track_index,
        }

        logger.info(
            "[Worker] transcribe_track complete",
            track_index=track_index,
            word_count=len(words),
        )

        if transcript_id:
            emit_progress(
                transcript_id,
                "transcribe_track",
                "completed",
                task.workflow_instance_id,
            )

    except Exception as e:
        logger.error("[Worker] transcribe_track failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "transcribe_track", "failed", task.workflow_instance_id
            )

    return task_result
