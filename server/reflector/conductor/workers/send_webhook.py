"""Conductor worker: send_webhook - Send transcript completion webhook."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="send_webhook")
def send_webhook(task: Task) -> TaskResult:
    """Send the transcript completion webhook to the configured URL.

    Input:
        transcript_id: str - Transcript ID
        room_id: str - Room ID

    Output:
        sent: bool - Whether webhook was sent
        status_code: int | None - HTTP status code
    """
    transcript_id = task.input_data.get("transcript_id")
    room_id = task.input_data.get("room_id")

    logger.info("[Worker] send_webhook", transcript_id=transcript_id, room_id=room_id)

    if transcript_id:
        emit_progress(
            transcript_id, "send_webhook", "in_progress", task.workflow_instance_id
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
        from reflector.db.rooms import rooms_controller
        from reflector.db.transcripts import transcripts_controller
        from reflector.settings import settings
        from reflector.worker.webhook import send_transcript_webhook

        # Create fresh database connection for subprocess (not shared from parent)
        _database_context.set(None)
        db = databases.Database(settings.DATABASE_URL)
        _database_context.set(db)
        await db.connect()

        try:
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript is None:
                raise ValueError(f"Transcript {transcript_id} not found in database")

            # Get room for webhook URL
            room = None
            if room_id:
                try:
                    room = await rooms_controller.get_by_id(room_id)
                except Exception:
                    pass

            if not room or not room.webhook_url:
                logger.info(
                    "[Worker] send_webhook: No webhook URL configured",
                    transcript_id=transcript_id,
                )
                return False, None

            status_code = await send_transcript_webhook(transcript, room)
            return True, status_code
        finally:
            await db.disconnect()
            _database_context.set(None)

    try:
        sent, status_code = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "sent": sent,
            "status_code": status_code,
        }

        logger.info(
            "[Worker] send_webhook complete",
            transcript_id=transcript_id,
            sent=sent,
            status_code=status_code,
        )

        if transcript_id:
            emit_progress(
                transcript_id, "send_webhook", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] send_webhook failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "send_webhook", "failed", task.workflow_instance_id
            )

    return task_result
