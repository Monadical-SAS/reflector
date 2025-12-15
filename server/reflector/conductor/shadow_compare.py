"""Shadow mode comparison for Celery vs Conductor pipeline results."""

from dataclasses import dataclass
from typing import Any

from reflector.conductor.client import ConductorClientManager
from reflector.db.transcripts import Transcript, transcripts_controller
from reflector.logger import logger


@dataclass
class FieldDifference:
    """A difference between Celery and Conductor field values."""

    field: str
    celery_value: Any
    conductor_value: Any


@dataclass
class ComparisonResult:
    """Result of comparing Celery and Conductor outputs."""

    match: bool
    differences: list[FieldDifference]
    celery_status: str
    conductor_status: str
    error: str | None = None


async def compare_content_results(
    recording_id: str, workflow_id: str
) -> ComparisonResult:
    """
    Compare content results from Celery and Conductor pipelines.

    Args:
        recording_id: Recording ID to look up Celery transcript
        workflow_id: Conductor workflow ID to get workflow output

    Returns:
        ComparisonResult with match status and any differences
    """
    try:
        # Get Celery result from DB
        celery_transcript = await transcripts_controller.get_by_recording_id(
            recording_id
        )
        if not celery_transcript:
            return ComparisonResult(
                match=False,
                differences=[],
                celery_status="not_found",
                conductor_status="unknown",
                error=f"No transcript found for recording_id={recording_id}",
            )

        # Get Conductor workflow status
        workflow_status = ConductorClientManager.get_workflow_status(workflow_id)
        conductor_status = workflow_status.status if workflow_status else "unknown"

        # If workflow not completed, can't compare
        if conductor_status != "COMPLETED":
            return ComparisonResult(
                match=False,
                differences=[],
                celery_status=celery_transcript.status,
                conductor_status=conductor_status,
                error=f"Conductor workflow not completed: {conductor_status}",
            )

        # Extract output from workflow
        workflow_output = (
            workflow_status.output if hasattr(workflow_status, "output") else {}
        )

        differences = _compare_fields(celery_transcript, workflow_output)

        result = ComparisonResult(
            match=len(differences) == 0,
            differences=differences,
            celery_status=celery_transcript.status,
            conductor_status=conductor_status,
        )

        # Log comparison result
        if result.match:
            logger.info(
                "Shadow mode comparison: MATCH",
                recording_id=recording_id,
                workflow_id=workflow_id,
            )
        else:
            logger.warning(
                "Shadow mode comparison: MISMATCH",
                recording_id=recording_id,
                workflow_id=workflow_id,
                differences=[
                    {
                        "field": d.field,
                        "celery": d.celery_value,
                        "conductor": d.conductor_value,
                    }
                    for d in differences
                ],
            )

        return result

    except Exception as e:
        logger.error(
            "Shadow mode comparison failed",
            recording_id=recording_id,
            workflow_id=workflow_id,
            error=str(e),
            exc_info=True,
        )
        return ComparisonResult(
            match=False,
            differences=[],
            celery_status="unknown",
            conductor_status="unknown",
            error=str(e),
        )


def _compare_fields(
    celery_transcript: Transcript, workflow_output: dict
) -> list[FieldDifference]:
    """Compare specific content fields between Celery and Conductor."""
    differences = []

    # Compare title
    conductor_title = workflow_output.get("title")
    if celery_transcript.title != conductor_title:
        differences.append(
            FieldDifference(
                field="title",
                celery_value=celery_transcript.title,
                conductor_value=conductor_title,
            )
        )

    # Compare short_summary
    conductor_short_summary = workflow_output.get("short_summary")
    if celery_transcript.short_summary != conductor_short_summary:
        differences.append(
            FieldDifference(
                field="short_summary",
                celery_value=celery_transcript.short_summary,
                conductor_value=conductor_short_summary,
            )
        )

    # Compare long_summary
    conductor_long_summary = workflow_output.get("summary")
    if celery_transcript.long_summary != conductor_long_summary:
        differences.append(
            FieldDifference(
                field="long_summary",
                celery_value=celery_transcript.long_summary,
                conductor_value=conductor_long_summary,
            )
        )

    # Compare topic count
    celery_topics = celery_transcript.topics or []
    conductor_topics = workflow_output.get("topics", [])
    if len(celery_topics) != len(conductor_topics):
        differences.append(
            FieldDifference(
                field="topic_count",
                celery_value=len(celery_topics),
                conductor_value=len(conductor_topics),
            )
        )

    # Compare word count from events
    celery_events = celery_transcript.events or {}
    celery_words = (
        celery_events.get("words", []) if isinstance(celery_events, dict) else []
    )
    conductor_words = workflow_output.get("all_words", [])
    if len(celery_words) != len(conductor_words):
        differences.append(
            FieldDifference(
                field="word_count",
                celery_value=len(celery_words),
                conductor_value=len(conductor_words),
            )
        )

    # Compare duration
    conductor_duration = workflow_output.get("duration")
    if (
        conductor_duration is not None
        and celery_transcript.duration != conductor_duration
    ):
        differences.append(
            FieldDifference(
                field="duration",
                celery_value=celery_transcript.duration,
                conductor_value=conductor_duration,
            )
        )

    return differences
