"""Progress event emission for Hatchet workers."""

from typing import Literal

from reflector.db.transcripts import PipelineProgressData
from reflector.logger import logger
from reflector.ws_manager import get_ws_manager

# Step mapping for progress tracking
PIPELINE_STEPS = {
    "get_recording": 1,
    "get_participants": 2,
    "pad_track": 3,  # Fork tasks share same step
    "mixdown_tracks": 4,
    "generate_waveform": 5,
    "transcribe_track": 6,  # Fork tasks share same step
    "merge_transcripts": 7,
    "detect_topics": 8,
    "generate_title": 9,  # Fork tasks share same step
    "generate_summary": 9,  # Fork tasks share same step
    "finalize": 10,
    "cleanup_consent": 11,
    "post_zulip": 12,
    "send_webhook": 13,
}

TOTAL_STEPS = 13


async def _emit_progress_async(
    transcript_id: str,
    step: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    workflow_id: str | None = None,
) -> None:
    """Async implementation of progress emission."""
    ws_manager = get_ws_manager()
    step_index = PIPELINE_STEPS.get(step, 0)

    data = PipelineProgressData(
        workflow_id=workflow_id,
        current_step=step,
        step_index=step_index,
        total_steps=TOTAL_STEPS,
        step_status=status,
    )

    await ws_manager.send_json(
        room_id=f"ts:{transcript_id}",
        message={
            "event": "PIPELINE_PROGRESS",
            "data": data.model_dump(),
        },
    )

    logger.debug(
        "[Hatchet Progress] Emitted",
        transcript_id=transcript_id,
        step=step,
        status=status,
        step_index=step_index,
    )


async def emit_progress_async(
    transcript_id: str,
    step: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    workflow_id: str | None = None,
) -> None:
    """Async version of emit_progress for use in async Hatchet tasks."""
    try:
        await _emit_progress_async(transcript_id, step, status, workflow_id)
    except Exception as e:
        logger.warning(
            "[Hatchet Progress] Failed to emit progress event",
            error=str(e),
            transcript_id=transcript_id,
            step=step,
        )
