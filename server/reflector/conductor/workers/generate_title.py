"""Conductor worker: generate_title - Generate meeting title using LLM."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="generate_title")
def generate_title(task: Task) -> TaskResult:
    """Generate meeting title from detected topics using LLM.

    Input:
        topics: list[dict] - Detected topics
        transcript_id: str - Transcript ID

    Output:
        title: str - Generated title
    """
    topics = task.input_data.get("topics", [])
    transcript_id = task.input_data.get("transcript_id")

    logger.info(
        "[Worker] generate_title",
        topic_count=len(topics),
        transcript_id=transcript_id,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "generate_title", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not topics:
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"title": "Untitled Meeting"}
        return task_result

    import asyncio

    async def _process():
        from reflector.pipelines import topic_processing
        from reflector.processors.types import TitleSummary, Word
        from reflector.processors.types import Transcript as TranscriptType

        # detect_topics returns TitleSummary objects (with transcript: Transcript)
        # When serialized, transcript becomes {translation, words} dict
        # We need to reconstruct TitleSummary objects with proper Transcript
        def normalize_topic(t):
            topic = dict(t)
            transcript_data = topic.get("transcript")
            if isinstance(transcript_data, dict):
                # Reconstruct Transcript object from serialized dict
                words_list = transcript_data.get("words", [])
                word_objects = [
                    Word(**w) if isinstance(w, dict) else w for w in words_list
                ]
                topic["transcript"] = TranscriptType(
                    words=word_objects, translation=transcript_data.get("translation")
                )
            elif transcript_data is None:
                topic["transcript"] = TranscriptType(words=[])
            return topic

        topic_objects = [TitleSummary(**normalize_topic(t)) for t in topics]
        empty_pipeline = topic_processing.EmptyPipeline(logger=logger)

        async def noop_callback(t):
            pass

        title = await topic_processing.generate_title(
            topic_objects,
            on_title_callback=noop_callback,
            empty_pipeline=empty_pipeline,
            logger=logger,
        )
        return title

    try:
        title = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {"title": title}

        logger.info(
            "[Worker] generate_title complete",
            transcript_id=transcript_id,
            title=title,
        )

        if transcript_id:
            emit_progress(
                transcript_id, "generate_title", "completed", task.workflow_instance_id
            )

    except Exception as e:
        logger.error("[Worker] generate_title failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "generate_title", "failed", task.workflow_instance_id
            )

    return task_result
