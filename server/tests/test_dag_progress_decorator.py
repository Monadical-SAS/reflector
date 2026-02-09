"""Tests for with_error_handling decorator integration with broadcast_dag_status.

The decorator wraps each pipeline task and calls broadcast_dag_status on both
success and failure paths. These tests verify that integration rather than
testing broadcast_dag_status in isolation (which test_dag_progress.py covers).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.hatchet.constants import TaskName


class TestWithErrorHandlingBroadcast:
    """Test with_error_handling decorator's integration with broadcast_dag_status."""

    @pytest.fixture(autouse=True)
    def _setup_hatchet_mock(self):
        """Set HatchetClientManager._instance to a mock to prevent real SDK init.

        Module-level code in workflow files calls get_client() during import.
        Setting _instance before import avoids ClientConfig validation.
        """
        from reflector.hatchet.client import HatchetClientManager

        original = HatchetClientManager._instance
        HatchetClientManager._instance = MagicMock()
        yield
        HatchetClientManager._instance = original

    def _make_input(self, transcript_id: str = "t-123") -> MagicMock:
        """Create a mock PipelineInput with transcript_id."""
        inp = MagicMock()
        inp.transcript_id = transcript_id
        return inp

    def _make_ctx(self, workflow_run_id: str = "wf-abc") -> MagicMock:
        """Create a mock Context with workflow_run_id."""
        ctx = MagicMock()
        ctx.workflow_run_id = workflow_run_id
        return ctx

    @pytest.mark.asyncio
    async def test_calls_broadcast_on_success(self):
        """Decorator calls broadcast_dag_status once when task succeeds."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            with_error_handling,
        )

        inner = AsyncMock(return_value="ok")
        wrapped = with_error_handling(TaskName.GET_RECORDING)(inner)

        with patch(
            "reflector.hatchet.dag_progress.broadcast_dag_status",
            new_callable=AsyncMock,
        ) as mock_broadcast:
            result = await wrapped(self._make_input(), self._make_ctx())

        assert result == "ok"
        mock_broadcast.assert_called_once_with("t-123", "wf-abc")

    @pytest.mark.asyncio
    async def test_calls_broadcast_on_failure(self):
        """Decorator calls broadcast_dag_status once when task raises."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            with_error_handling,
        )

        inner = AsyncMock(side_effect=RuntimeError("boom"))
        wrapped = with_error_handling(TaskName.GET_RECORDING)(inner)

        with (
            patch(
                "reflector.hatchet.dag_progress.broadcast_dag_status",
                new_callable=AsyncMock,
            ) as mock_broadcast,
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.set_workflow_error_status",
                new_callable=AsyncMock,
            ),
        ):
            with pytest.raises(RuntimeError, match="boom"):
                await wrapped(self._make_input(), self._make_ctx())

        mock_broadcast.assert_called_once_with("t-123", "wf-abc")

    @pytest.mark.asyncio
    async def test_swallows_broadcast_exception_on_success(self):
        """Broadcast failure does not crash the task on the success path."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            with_error_handling,
        )

        inner = AsyncMock(return_value="ok")
        wrapped = with_error_handling(TaskName.GET_RECORDING)(inner)

        with patch(
            "reflector.hatchet.dag_progress.broadcast_dag_status",
            new_callable=AsyncMock,
            side_effect=RuntimeError("broadcast exploded"),
        ):
            result = await wrapped(self._make_input(), self._make_ctx())

        assert result == "ok"

    @pytest.mark.asyncio
    async def test_swallows_broadcast_exception_on_failure(self):
        """Original task exception propagates even when broadcast also fails."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            with_error_handling,
        )

        inner = AsyncMock(side_effect=ValueError("original error"))
        wrapped = with_error_handling(TaskName.GET_RECORDING)(inner)

        with (
            patch(
                "reflector.hatchet.dag_progress.broadcast_dag_status",
                new_callable=AsyncMock,
                side_effect=RuntimeError("broadcast exploded"),
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.set_workflow_error_status",
                new_callable=AsyncMock,
            ),
        ):
            with pytest.raises(ValueError, match="original error"):
                await wrapped(self._make_input(), self._make_ctx())

    @pytest.mark.asyncio
    async def test_calls_set_workflow_error_status_on_failure(self):
        """On task failure with set_error_status=True (default), calls set_workflow_error_status."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            with_error_handling,
        )

        inner = AsyncMock(side_effect=RuntimeError("boom"))
        wrapped = with_error_handling(TaskName.GET_RECORDING)(inner)

        with (
            patch(
                "reflector.hatchet.dag_progress.broadcast_dag_status",
                new_callable=AsyncMock,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.set_workflow_error_status",
                new_callable=AsyncMock,
            ) as mock_set_error,
        ):
            with pytest.raises(RuntimeError, match="boom"):
                await wrapped(self._make_input(), self._make_ctx())

        mock_set_error.assert_called_once_with("t-123")

    @pytest.mark.asyncio
    async def test_no_set_workflow_error_status_when_disabled(self):
        """With set_error_status=False, set_workflow_error_status is NOT called on failure."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            with_error_handling,
        )

        inner = AsyncMock(side_effect=RuntimeError("boom"))
        wrapped = with_error_handling(TaskName.GET_RECORDING, set_error_status=False)(
            inner
        )

        with (
            patch(
                "reflector.hatchet.dag_progress.broadcast_dag_status",
                new_callable=AsyncMock,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.set_workflow_error_status",
                new_callable=AsyncMock,
            ) as mock_set_error,
        ):
            with pytest.raises(RuntimeError, match="boom"):
                await wrapped(self._make_input(), self._make_ctx())

        mock_set_error.assert_not_called()
