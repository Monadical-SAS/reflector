"""
Tests for Hatchet progress emission.

Only tests that catch real bugs - error handling and step completeness.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.asyncio
async def test_emit_progress_async_handles_exception():
    """Test that emit_progress_async catches exceptions gracefully.

    Critical: Progress emission must NEVER crash the pipeline.
    WebSocket errors should be silently caught.
    """
    from reflector.hatchet.progress import emit_progress_async

    with patch("reflector.hatchet.progress.get_ws_manager") as mock_get_ws:
        mock_ws = MagicMock()
        mock_ws.send_json = AsyncMock(side_effect=Exception("WebSocket error"))
        mock_get_ws.return_value = mock_ws

        # Should not raise - exceptions are caught
        await emit_progress_async(
            transcript_id="test-transcript-123",
            step="finalize",
            status="completed",
        )


@pytest.mark.asyncio
async def test_pipeline_steps_mapping_complete():
    """Test the PIPELINE_STEPS mapping includes all expected steps.

    Useful: Catches when someone adds a new pipeline step but forgets
    to add it to the progress mapping, resulting in missing UI updates.
    """
    from reflector.hatchet.progress import PIPELINE_STEPS, TOTAL_STEPS

    expected_steps = [
        "get_recording",
        "get_participants",
        "pad_track",
        "mixdown_tracks",
        "generate_waveform",
        "transcribe_track",
        "merge_transcripts",
        "detect_topics",
        "generate_title",
        "generate_summary",
        "finalize",
        "cleanup_consent",
        "post_zulip",
        "send_webhook",
    ]

    for step in expected_steps:
        assert step in PIPELINE_STEPS, f"Missing step in PIPELINE_STEPS: {step}"
        assert 1 <= PIPELINE_STEPS[step] <= TOTAL_STEPS
