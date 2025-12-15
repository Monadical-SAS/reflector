"""Progress event emission for Conductor workers."""

import asyncio
from typing import Literal

from reflector.db.transcripts import PipelineProgressData
from reflector.logger import logger
from reflector.ws_manager import get_ws_manager

# Step mapping for progress tracking
# Maps task names to their index in the pipeline
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
        "[Progress] Emitted",
        transcript_id=transcript_id,
        step=step,
        status=status,
        step_index=step_index,
    )


def emit_progress(
    transcript_id: str,
    step: str,
    status: Literal["pending", "in_progress", "completed", "failed"],
    workflow_id: str | None = None,
) -> None:
    """Emit a pipeline progress event (sync wrapper for Conductor workers).

    Args:
        transcript_id: The transcript ID to emit progress for
        step: The current step name (e.g., "transcribe_track")
        status: The step status
        workflow_id: Optional workflow ID
    """
    try:
        # Get or create event loop for sync context
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop is not None and loop.is_running():
            # Already in async context, schedule the coroutine
            asyncio.create_task(
                _emit_progress_async(transcript_id, step, status, workflow_id)
            )
        else:
            # Not in async context, run synchronously
            asyncio.run(_emit_progress_async(transcript_id, step, status, workflow_id))
    except Exception as e:
        # Progress emission should never break the pipeline
        logger.warning(
            "[Progress] Failed to emit progress event",
            error=str(e),
            transcript_id=transcript_id,
            step=step,
        )
