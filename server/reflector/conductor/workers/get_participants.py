"""Conductor worker: get_participants - Fetch meeting participants from Daily.co API."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.dailyco_api.client import DailyApiClient
from reflector.logger import logger
from reflector.settings import settings


@worker_task(task_definition_name="get_participants")
def get_participants(task: Task) -> TaskResult:
    """Fetch meeting participants from Daily.co API.

    Input:
        mtg_session_id: str - Daily.co meeting session identifier
        transcript_id: str - Transcript ID for progress tracking

    Output:
        participants: list[dict] - List of participant info
            - participant_id: str
            - user_name: str | None
            - user_id: str | None
    """
    mtg_session_id = task.input_data.get("mtg_session_id")
    transcript_id = task.input_data.get("transcript_id")

    logger.info("[Worker] get_participants", mtg_session_id=mtg_session_id)

    if transcript_id:
        emit_progress(
            transcript_id, "get_participants", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not mtg_session_id:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing mtg_session_id"
        return task_result

    if not settings.DAILY_API_KEY:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "DAILY_API_KEY not configured"
        return task_result

    import asyncio

    async def _fetch():
        async with DailyApiClient(api_key=settings.DAILY_API_KEY) as client:
            return await client.get_meeting_participants(mtg_session_id)

    try:
        response = asyncio.run(_fetch())

        participants = [
            {
                "participant_id": p.participant_id,
                "user_name": p.user_name,
                "user_id": p.user_id,
            }
            for p in response.data
        ]

        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"participants": participants}

        logger.info(
            "[Worker] get_participants complete",
            mtg_session_id=mtg_session_id,
            count=len(participants),
        )

        if transcript_id:
            emit_progress(
                transcript_id,
                "get_participants",
                "completed",
                task.workflow_instance_id,
            )

    except Exception as e:
        logger.error("[Worker] get_participants failed", error=str(e))
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "get_participants", "failed", task.workflow_instance_id
            )

    return task_result
