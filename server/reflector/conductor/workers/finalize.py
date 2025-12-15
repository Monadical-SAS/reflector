"""Conductor worker: finalize - Finalize transcript status and update database."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="finalize")
def finalize(task: Task) -> TaskResult:
    """Finalize the transcript status and update the database.

    Input:
        transcript_id: str - Transcript ID
        title: str - Generated title
        summary: str - Long summary
        short_summary: str - Short summary
        duration: float - Audio duration

    Output:
        status: str - "COMPLETED"
    """
    transcript_id = task.input_data.get("transcript_id")
    title = task.input_data.get("title", "")
    summary = task.input_data.get("summary", "")
    short_summary = task.input_data.get("short_summary", "")
    duration = task.input_data.get("duration", 0)

    logger.info(
        "[Worker] finalize",
        transcript_id=transcript_id,
        title=title,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "finalize", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not transcript_id:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing transcript_id"
        return task_result

    import asyncio

    async def _process():
        import databases

        from reflector.db import _database_context
        from reflector.db.transcripts import transcripts_controller
        from reflector.settings import settings

        # Create fresh database connection for subprocess (not shared from parent)
        _database_context.set(None)
        db = databases.Database(settings.DATABASE_URL)
        _database_context.set(db)
        await db.connect()

        try:
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript is None:
                raise ValueError(f"Transcript {transcript_id} not found in database")

            await transcripts_controller.update(
                transcript,
                {
                    "status": "ended",
                    "title": title,
                    "long_summary": summary,
                    "short_summary": short_summary,
                    "duration": duration,
                },
            )
            return True
        finally:
            await db.disconnect()
            _database_context.set(None)

    try:
        asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"status": "COMPLETED"}

        logger.info(
            "[Worker] finalize complete",
            transcript_id=transcript_id,
        )

        if transcript_id:
            emit_progress(
                transcript_id, "finalize", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] finalize failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "finalize", "failed", task.workflow_instance_id
            )

    return task_result
