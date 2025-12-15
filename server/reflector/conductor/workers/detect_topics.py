"""Conductor worker: detect_topics - Detect topics using LLM."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="detect_topics")
def detect_topics(task: Task) -> TaskResult:
    """Detect topics using LLM.

    Input:
        words: list[dict] - Transcribed words
        transcript_id: str - Transcript ID
        target_language: str - Target language code (default: "en")

    Output:
        topics: list[dict] - Detected topics
    """
    words = task.input_data.get("words", [])
    transcript_id = task.input_data.get("transcript_id")
    target_language = task.input_data.get("target_language", "en")

    logger.info(
        "[Worker] detect_topics",
        word_count=len(words),
        transcript_id=transcript_id,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "detect_topics", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    import asyncio

    async def _process():
        from reflector.pipelines import topic_processing
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.processors.types import Word

        # Convert word dicts to Word objects
        word_objects = [Word(**w) for w in words]
        transcript = TranscriptType(words=word_objects)

        empty_pipeline = topic_processing.EmptyPipeline(logger=logger)

        async def noop_callback(t):
            pass

        topics = await topic_processing.detect_topics(
            transcript,
            target_language,
            on_topic_callback=noop_callback,
            empty_pipeline=empty_pipeline,
        )

        return [t.model_dump() for t in topics]

    try:
        topics = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"topics": topics}

        logger.info(
            "[Worker] detect_topics complete",
            transcript_id=transcript_id,
            topic_count=len(topics),
        )

        if transcript_id:
            emit_progress(
                transcript_id, "detect_topics", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] detect_topics failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "detect_topics", "failed", task.workflow_instance_id
            )

    return task_result
