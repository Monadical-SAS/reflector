"""Conductor worker: post_zulip - Post or update Zulip message with transcript summary."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger
from reflector.settings import settings


@worker_task(task_definition_name="post_zulip")
def post_zulip(task: Task) -> TaskResult:
    """Post or update a Zulip message with the transcript summary.

    Input:
        transcript_id: str - Transcript ID

    Output:
        message_id: str | None - Zulip message ID
    """
    transcript_id = task.input_data.get("transcript_id")

    logger.info("[Worker] post_zulip", transcript_id=transcript_id)

    if transcript_id:
        emit_progress(
            transcript_id, "post_zulip", "in_progress", task.workflow_instance_id
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

    # Check if Zulip is configured
    if not settings.ZULIP_REALM or not settings.ZULIP_API_KEY:
        logger.info("[Worker] post_zulip: Zulip not configured, skipping")
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"message_id": None}
        return task_result

    import asyncio

    async def _process():
        import databases

        from reflector.db import _database_context
        from reflector.db.transcripts import transcripts_controller
        from reflector.settings import settings as app_settings
        from reflector.zulip import post_transcript_to_zulip

        # Create fresh database connection for subprocess (not shared from parent)
        _database_context.set(None)
        db = databases.Database(app_settings.DATABASE_URL)
        _database_context.set(db)
        await db.connect()

        try:
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript is None:
                raise ValueError(f"Transcript {transcript_id} not found in database")
            message_id = await post_transcript_to_zulip(transcript)
            return message_id
        finally:
            await db.disconnect()
            _database_context.set(None)

    try:
        message_id = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "message_id": str(message_id) if message_id else None
        }

        logger.info(
            "[Worker] post_zulip complete",
            transcript_id=transcript_id,
            message_id=message_id,
        )

        if transcript_id:
            emit_progress(
                transcript_id, "post_zulip", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] post_zulip failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "post_zulip", "failed", task.workflow_instance_id
            )

    return task_result
