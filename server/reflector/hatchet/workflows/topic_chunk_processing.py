"""
Hatchet child workflow: TopicChunkProcessing

Handles topic detection for individual transcript chunks.
Spawned dynamically by detect_topics via aio_run_many() for parallel processing.
"""

from datetime import timedelta

from hatchet_sdk import Context
from hatchet_sdk.rate_limit import RateLimit
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.constants import LLM_RATE_LIMIT_KEY, TIMEOUT_SHORT
from reflector.hatchet.workflows.models import TopicChunkResult
from reflector.logger import logger
from reflector.processors.prompts import TOPIC_PROMPT
from reflector.processors.types import Word


class TopicChunkInput(BaseModel):
    """Input for individual topic chunk processing."""

    chunk_index: int
    chunk_text: str
    timestamp: float
    duration: float
    words: list[Word]


hatchet = HatchetClientManager.get_client()

topic_chunk_workflow = hatchet.workflow(
    name="TopicChunkProcessing", input_validator=TopicChunkInput
)


@topic_chunk_workflow.task(
    execution_timeout=timedelta(seconds=TIMEOUT_SHORT),
    retries=3,
    rate_limits=[RateLimit(static_key=LLM_RATE_LIMIT_KEY, units=1)],
)
async def detect_chunk_topic(input: TopicChunkInput, ctx: Context) -> TopicChunkResult:
    """Detect topic for a single transcript chunk."""
    ctx.log(f"detect_chunk_topic: chunk {input.chunk_index}")
    logger.info(
        "[Hatchet] detect_chunk_topic",
        chunk_index=input.chunk_index,
        text_length=len(input.chunk_text),
    )

    # Deferred imports: Hatchet workers fork processes, fresh imports avoid
    # sharing LLM HTTP connection pools across forks
    from reflector.llm import LLM  # noqa: PLC0415
    from reflector.processors.transcript_topic_detector import (  # noqa: PLC0415
        TopicResponse,
    )
    from reflector.settings import settings  # noqa: PLC0415
    from reflector.utils.text import clean_title  # noqa: PLC0415

    llm = LLM(settings=settings, temperature=0.9, max_tokens=500)

    prompt = TOPIC_PROMPT.format(text=input.chunk_text)
    response = await llm.get_structured_response(
        prompt,
        [input.chunk_text],
        TopicResponse,
        tone_name="Topic analyzer",
        timeout=settings.LLM_STRUCTURED_RESPONSE_TIMEOUT,
    )

    title = clean_title(response.title)

    ctx.log(
        f"detect_chunk_topic complete: chunk {input.chunk_index}, title='{title[:50]}'"
    )
    logger.info(
        "[Hatchet] detect_chunk_topic complete",
        chunk_index=input.chunk_index,
        title=title[:50],
    )

    return TopicChunkResult(
        chunk_index=input.chunk_index,
        title=title,
        summary=response.summary,
        timestamp=input.timestamp,
        duration=input.duration,
        words=input.words,
    )
