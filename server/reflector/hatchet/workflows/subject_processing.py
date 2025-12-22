"""
Hatchet child workflow: SubjectProcessing

Handles individual subject/topic summary generation.
Spawned dynamically by the main diarization pipeline for each extracted subject
via aio_run_many() for parallel processing.
"""

from datetime import timedelta

from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.models import SubjectSummaryResult
from reflector.logger import logger
from reflector.processors.summary.prompts import (
    DETAILED_SUBJECT_PROMPT_TEMPLATE,
    PARAGRAPH_SUMMARY_PROMPT,
    build_participant_instructions,
)


class SubjectInput(BaseModel):
    """Input for individual subject processing."""

    subject: str
    subject_index: int
    transcript_text: str
    participant_names: list[str]
    participant_name_to_id: dict[str, str]


hatchet = HatchetClientManager.get_client()

subject_workflow = hatchet.workflow(
    name="SubjectProcessing", input_validator=SubjectInput
)


@subject_workflow.task(execution_timeout=timedelta(seconds=120), retries=3)
async def generate_detailed_summary(
    input: SubjectInput, ctx: Context
) -> SubjectSummaryResult:
    """Generate detailed analysis for a single subject, then condense to paragraph."""
    ctx.log(
        f"generate_detailed_summary: subject '{input.subject}' (index {input.subject_index})"
    )
    logger.info(
        "[Hatchet] generate_detailed_summary",
        subject=input.subject,
        subject_index=input.subject_index,
    )

    # Deferred imports: Hatchet workers fork processes, fresh imports ensure
    # LLM HTTP connection pools aren't shared across forks
    from reflector.llm import LLM  # noqa: PLC0415
    from reflector.settings import settings  # noqa: PLC0415

    llm = LLM(settings=settings)

    participant_instructions = build_participant_instructions(input.participant_names)
    detailed_prompt = DETAILED_SUBJECT_PROMPT_TEMPLATE.format(subject=input.subject)
    if participant_instructions:
        detailed_prompt = f"{detailed_prompt}\n\n{participant_instructions}"

    ctx.log("generate_detailed_summary: calling LLM for detailed analysis")
    detailed_response = await llm.get_response(
        detailed_prompt,
        [input.transcript_text],
        tone_name="Topic assistant",
    )
    detailed_summary = str(detailed_response)

    paragraph_prompt = PARAGRAPH_SUMMARY_PROMPT
    if participant_instructions:
        paragraph_prompt = f"{paragraph_prompt}\n\n{participant_instructions}"

    ctx.log("generate_detailed_summary: calling LLM for paragraph summary")
    paragraph_response = await llm.get_response(
        paragraph_prompt,
        [detailed_summary],
        tone_name="Topic summarizer",
    )
    paragraph_summary = str(paragraph_response)

    ctx.log(f"generate_detailed_summary complete: subject '{input.subject}'")
    logger.info(
        "[Hatchet] generate_detailed_summary complete",
        subject=input.subject,
        subject_index=input.subject_index,
        detailed_len=len(detailed_summary),
        paragraph_len=len(paragraph_summary),
    )

    return SubjectSummaryResult(
        subject=input.subject,
        subject_index=input.subject_index,
        detailed_summary=detailed_summary,
        paragraph_summary=paragraph_summary,
    )
