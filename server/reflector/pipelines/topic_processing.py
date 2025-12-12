"""
Topic processing utilities
==========================

Shared topic detection, title generation, and summarization logic
used across file and multitrack pipelines.
"""

from typing import Callable

import structlog

from reflector.db.transcripts import Transcript
from reflector.processors import (
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptTopicDetectorProcessor,
)
from reflector.processors.types import TitleSummary
from reflector.processors.types import Transcript as TranscriptType


class EmptyPipeline:
    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def get_pref(self, k, d=None):
        return d

    async def emit(self, event):
        pass


async def detect_topics(
    transcript: TranscriptType,
    target_language: str,
    *,
    on_topic_callback: Callable,
    empty_pipeline: EmptyPipeline,
) -> list[TitleSummary]:
    chunk_size = 300
    topics: list[TitleSummary] = []

    async def on_topic(topic: TitleSummary):
        topics.append(topic)
        return await on_topic_callback(topic)

    topic_detector = TranscriptTopicDetectorProcessor(callback=on_topic)
    topic_detector.set_pipeline(empty_pipeline)

    for i in range(0, len(transcript.words), chunk_size):
        chunk_words = transcript.words[i : i + chunk_size]
        if not chunk_words:
            continue

        chunk_transcript = TranscriptType(
            words=chunk_words, translation=transcript.translation
        )

        await topic_detector.push(chunk_transcript)

    await topic_detector.flush()
    return topics


async def generate_title(
    topics: list[TitleSummary],
    *,
    on_title_callback: Callable,
    empty_pipeline: EmptyPipeline,
    logger: structlog.BoundLogger,
):
    if not topics:
        logger.warning("No topics for title generation")
        return

    processor = TranscriptFinalTitleProcessor(callback=on_title_callback)
    processor.set_pipeline(empty_pipeline)

    for topic in topics:
        await processor.push(topic)

    await processor.flush()


async def generate_summaries(
    topics: list[TitleSummary],
    transcript: Transcript,
    *,
    on_long_summary_callback: Callable,
    on_short_summary_callback: Callable,
    on_action_items_callback: Callable | None = None,
    empty_pipeline: EmptyPipeline,
    logger: structlog.BoundLogger,
):
    if not topics:
        logger.warning("No topics for summary generation")
        return

    processor_kwargs = {
        "transcript": transcript,
        "callback": on_long_summary_callback,
        "on_short_summary": on_short_summary_callback,
    }
    if on_action_items_callback:
        processor_kwargs["on_action_items"] = on_action_items_callback

    processor = TranscriptFinalSummaryProcessor(**processor_kwargs)
    processor.set_pipeline(empty_pipeline)

    for topic in topics:
        await processor.push(topic)

    await processor.flush()
