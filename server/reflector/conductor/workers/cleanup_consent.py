"""Conductor worker: cleanup_consent - Check consent and delete audio if denied."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="cleanup_consent")
def cleanup_consent(task: Task) -> TaskResult:
    """Check participant consent and delete audio if denied.

    Input:
        transcript_id: str - Transcript ID

    Output:
        audio_deleted: bool - Whether audio was deleted
        reason: str | None - Reason for deletion
    """
    transcript_id = task.input_data.get("transcript_id")

    logger.info("[Worker] cleanup_consent", transcript_id=transcript_id)

    if transcript_id:
        emit_progress(
            transcript_id, "cleanup_consent", "in_progress", task.workflow_instance_id
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
        from reflector.storage import get_transcripts_storage

        # Create fresh database connection for subprocess (not shared from parent)
        _database_context.set(None)
        db = databases.Database(settings.DATABASE_URL)
        _database_context.set(db)
        await db.connect()

        try:
            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript is None:
                raise ValueError(f"Transcript {transcript_id} not found in database")

            # Check if any participant denied consent
            # This mirrors the logic from main_live_pipeline.task_cleanup_consent
            audio_deleted = False
            reason = None

            if transcript.participants:
                for p in transcript.participants:
                    if hasattr(p, "consent") and p.consent == "denied":
                        audio_deleted = True
                        reason = f"Participant {p.name or p.id} denied consent"
                        break

            if audio_deleted:
                storage = get_transcripts_storage()
                audio_key = f"{transcript_id}/audio.mp3"
                try:
                    await storage.delete_file(audio_key)
                    await transcripts_controller.update(
                        transcript, {"audio_deleted": True}
                    )
                    logger.info(
                        "[Worker] cleanup_consent: audio deleted",
                        transcript_id=transcript_id,
                        reason=reason,
                    )
                except Exception as e:
                    logger.warning(
                        "[Worker] cleanup_consent: failed to delete audio",
                        error=str(e),
                    )

            return audio_deleted, reason
        finally:
            await db.disconnect()
            _database_context.set(None)

    try:
        audio_deleted, reason = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "audio_deleted": audio_deleted,
            "reason": reason,
        }

        logger.info(
            "[Worker] cleanup_consent complete",
            transcript_id=transcript_id,
            audio_deleted=audio_deleted,
        )

        if transcript_id:
            emit_progress(
                transcript_id, "cleanup_consent", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] cleanup_consent failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "cleanup_consent", "failed", task.workflow_instance_id
            )

    return task_result
