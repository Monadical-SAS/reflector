"""Conductor worker: get_recording - Fetch recording metadata from Daily.co API."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.dailyco_api.client import DailyApiClient
from reflector.logger import logger
from reflector.settings import settings


@worker_task(task_definition_name="get_recording")
def get_recording(task: Task) -> TaskResult:
    """Fetch recording metadata from Daily.co API.

    Input:
        recording_id: str - Daily.co recording identifier
        transcript_id: str - Transcript ID for progress tracking

    Output:
        id: str - Recording ID
        mtg_session_id: str - Meeting session ID
        room_name: str - Room name
        duration: int - Recording duration in seconds
    """
    recording_id = task.input_data.get("recording_id")
    transcript_id = task.input_data.get("transcript_id")

    logger.info("[Worker] get_recording", recording_id=recording_id)

    if transcript_id:
        emit_progress(
            transcript_id, "get_recording", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not recording_id:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing recording_id"
        return task_result

    if not settings.DAILY_API_KEY:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "DAILY_API_KEY not configured"
        return task_result

    import asyncio

    async def _fetch():
        async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
            return await client.get_recording(recording_id)

    try:
        recording = asyncio.run(_fetch())

        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "id": recording.id,
            "mtg_session_id": recording.mtgSessionId,
            "room_name": recording.room_name,
            "duration": recording.duration,
        }

        logger.info(
            "[Worker] get_recording complete",
            recording_id=recording_id,
            room_name=recording.room_name,
            duration=recording.duration,
        )

        if transcript_id:
            emit_progress(
                transcript_id, "get_recording", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] get_recording failed", error=str(e))
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "get_recording", "failed", task.workflow_instance_id
            )

    return task_result
