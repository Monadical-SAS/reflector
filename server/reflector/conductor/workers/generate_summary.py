"""Conductor worker: generate_summary - Generate meeting summaries using LLM."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.conductor.progress import emit_progress
from reflector.logger import logger


@worker_task(task_definition_name="generate_summary")
def generate_summary(task: Task) -> TaskResult:
    """Generate long and short summaries from topics and words using LLM.

    Input:
        words: list[dict] - Transcribed words
        topics: list[dict] - Detected topics
        transcript_id: str - Transcript ID

    Output:
        summary: str - Long summary
        short_summary: str - Short summary
    """
    words = task.input_data.get("words", [])
    topics = task.input_data.get("topics", [])
    transcript_id = task.input_data.get("transcript_id")

    logger.info(
        "[Worker] generate_summary",
        word_count=len(words),
        topic_count=len(topics),
        transcript_id=transcript_id,
    )

    if transcript_id:
        emit_progress(
            transcript_id, "generate_summary", "in_progress", task.workflow_instance_id
        )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    import asyncio

    async def _process():
        import databases

        from reflector.db import _database_context
        from reflector.db.transcripts import transcripts_controller
        from reflector.pipelines import topic_processing
        from reflector.processors.types import TitleSummary, Word
        from reflector.processors.types import Transcript as TranscriptType
        from reflector.settings import settings

        # Create fresh database connection for subprocess (not shared from parent)
        # Reset context var to ensure we get a fresh connection
        _database_context.set(None)
        db = databases.Database(settings.DATABASE_URL)
        _database_context.set(db)
        await db.connect()

        try:
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
                        words=word_objects,
                        translation=transcript_data.get("translation"),
                    )
                elif transcript_data is None:
                    topic["transcript"] = TranscriptType(words=[])
                return topic

            topic_objects = [TitleSummary(**normalize_topic(t)) for t in topics]
            empty_pipeline = topic_processing.EmptyPipeline(logger=logger)

            transcript = await transcripts_controller.get_by_id(transcript_id)

            long_summary = ""
            short_summary = ""

            async def on_long(s):
                nonlocal long_summary
                # s is FinalLongSummary object
                long_summary = s.long_summary if hasattr(s, "long_summary") else str(s)

            async def on_short(s):
                nonlocal short_summary
                # s is FinalShortSummary object
                short_summary = (
                    s.short_summary if hasattr(s, "short_summary") else str(s)
                )

            await topic_processing.generate_summaries(
                topic_objects,
                transcript,
                on_long_summary_callback=on_long,
                on_short_summary_callback=on_short,
                empty_pipeline=empty_pipeline,
                logger=logger,
            )

            return long_summary, short_summary
        finally:
            await db.disconnect()
            _database_context.set(None)

    try:
        summary, short_summary = asyncio.run(_process())
        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "summary": summary,
            "short_summary": short_summary,
        }

        logger.info(
            "[Worker] generate_summary complete",
            transcript_id=transcript_id,
            summary_len=len(summary) if summary else 0,
        )

        if transcript_id:
            emit_progress(
                transcript_id,
                "generate_summary",
                "completed",
                task.workflow_instance_id,
            )

    except Exception as e:
        logger.error("[Worker] generate_summary failed", error=str(e), exc_info=True)
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)
        if transcript_id:
            emit_progress(
                transcript_id, "generate_summary", "failed", task.workflow_instance_id
            )

    return task_result
