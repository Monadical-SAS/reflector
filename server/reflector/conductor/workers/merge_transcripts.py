"""Conductor worker: merge_transcripts - Merge multiple track transcriptions."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="merge_transcripts")
def merge_transcripts(task: Task) -> TaskResult:
    """Merge multiple track transcriptions into single timeline sorted by timestamp.

    Input:
        transcripts: list[dict] - List of transcription results with words
        transcript_id: str - Transcript ID

    Output:
        all_words: list[dict] - Merged and sorted words
        word_count: int - Total word count
    """
    transcripts = task.input_data.get("transcripts", [])
    transcript_id = task.input_data.get("transcript_id")

    logger.info(
        "[Worker] merge_transcripts",
        transcript_count=len(transcripts)
        if isinstance(transcripts, (list, dict))
        else 0,
        transcript_id=transcript_id,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "merge_transcripts", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    try:
        all_words = []

        # Handle JOIN output (dict with task refs as keys)
        if isinstance(transcripts, dict):
            transcripts = list(transcripts.values())

        for t in transcripts:
            if isinstance(t, list):
                all_words.extend(t)
            elif isinstance(t, dict) and "words" in t:
                all_words.extend(t["words"])

        # Sort by start timestamp
        all_words.sort(key=lambda w: w.get("start", 0))

        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "all_words": all_words,
            "word_count": len(all_words),
        }

        logger.info(
            "[Worker] merge_transcripts complete",
            transcript_id=transcript_id,
            word_count=len(all_words),
        )

        if transcript_id:
            emit_progress(
                transcript_id,
                "merge_transcripts",
                "completed",
                task.workflow_instance_id,
            )

    except Exception as e:
        logger.error("[Worker] merge_transcripts failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "merge_transcripts", "failed", task.workflow_instance_id
            )

    return task_result
