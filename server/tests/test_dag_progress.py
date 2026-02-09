"""Tests for DAG progress models and transform function.

Tests the extract_dag_tasks function that converts Hatchet V1WorkflowRunDetails
into structured DagTask list for frontend consumption.
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from reflector.hatchet.constants import TaskName
from reflector.hatchet.dag_progress import (
    DagStatusData,
    DagTask,
    DagTaskStatus,
    extract_dag_tasks,
)


def _make_shape_item(
    step_id: str,
    task_name: str,
    children_step_ids: list[str] | None = None,
) -> MagicMock:
    """Create a mock WorkflowRunShapeItemForWorkflowRunDetails."""
    item = MagicMock()
    item.step_id = step_id
    item.task_name = task_name
    item.children_step_ids = children_step_ids or []
    return item


def _make_task_summary(
    step_id: str,
    status: str = "QUEUED",
    started_at: datetime | None = None,
    finished_at: datetime | None = None,
    duration: int | None = None,
    error_message: str | None = None,
    task_external_id: str | None = None,
    num_spawned_children: int | None = None,
    children: list | None = None,
) -> MagicMock:
    """Create a mock V1TaskSummary."""
    from hatchet_sdk.clients.rest.models import V1TaskStatus

    task = MagicMock()
    task.step_id = step_id
    task.status = V1TaskStatus(status)
    task.started_at = started_at
    task.finished_at = finished_at
    task.duration = duration
    task.error_message = error_message
    task.task_external_id = task_external_id or f"ext-{step_id}"
    task.num_spawned_children = num_spawned_children
    task.children = children or []
    return task


def _make_details(
    shape: list,
    tasks: list,
    run_id: str = "test-run-id",
) -> MagicMock:
    """Create a mock V1WorkflowRunDetails."""
    details = MagicMock()
    details.shape = shape
    details.tasks = tasks
    details.task_events = []
    details.run = MagicMock()
    details.run.metadata = MagicMock()
    details.run.metadata.id = run_id
    return details


class TestExtractDagTasksBasic:
    """Test basic extraction of DAG tasks from workflow run details."""

    def test_empty_shape_returns_empty_list(self):
        details = _make_details(shape=[], tasks=[])
        result = extract_dag_tasks(details)
        assert result == []

    def test_single_task_queued(self):
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = [_make_task_summary("s1", status="QUEUED")]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert len(result) == 1
        assert result[0].name == "get_recording"
        assert result[0].status == DagTaskStatus.QUEUED
        assert result[0].parents == []
        assert result[0].started_at is None
        assert result[0].finished_at is None
        assert result[0].duration_seconds is None
        assert result[0].error is None
        assert result[0].children_total is None
        assert result[0].children_completed is None
        assert result[0].progress_pct is None

    def test_completed_task_with_duration(self):
        now = datetime.now(timezone.utc)
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = [
            _make_task_summary(
                "s1",
                status="COMPLETED",
                started_at=now,
                finished_at=now,
                duration=1500,  # milliseconds
            )
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].status == DagTaskStatus.COMPLETED
        assert result[0].duration_seconds == 1.5
        assert result[0].started_at == now
        assert result[0].finished_at == now

    def test_failed_task_with_error(self):
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = [
            _make_task_summary(
                "s1",
                status="FAILED",
                error_message="Traceback (most recent call last):\n  File something\nConnectionError: connection refused",
            )
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].status == DagTaskStatus.FAILED
        assert result[0].error == "ConnectionError: connection refused"

    def test_running_task(self):
        now = datetime.now(timezone.utc)
        shape = [_make_shape_item("s1", "mixdown_tracks")]
        tasks = [
            _make_task_summary(
                "s1",
                status="RUNNING",
                started_at=now,
                duration=5000,
            )
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].status == DagTaskStatus.RUNNING
        assert result[0].started_at == now
        assert result[0].duration_seconds == 5.0

    def test_cancelled_task(self):
        shape = [_make_shape_item("s1", "post_zulip")]
        tasks = [_make_task_summary("s1", status="CANCELLED")]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].status == DagTaskStatus.CANCELLED


class TestExtractDagTasksTopology:
    """Test topological ordering and parent extraction."""

    def test_linear_chain_parents(self):
        """A -> B -> C should produce correct parents."""
        shape = [
            _make_shape_item("s1", "get_recording", children_step_ids=["s2"]),
            _make_shape_item("s2", "get_participants", children_step_ids=["s3"]),
            _make_shape_item("s3", "process_tracks"),
        ]
        tasks = [
            _make_task_summary("s1", status="COMPLETED"),
            _make_task_summary("s2", status="COMPLETED"),
            _make_task_summary("s3", status="QUEUED"),
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert [t.name for t in result] == [
            "get_recording",
            "get_participants",
            "process_tracks",
        ]
        assert result[0].parents == []
        assert result[1].parents == ["get_recording"]
        assert result[2].parents == ["get_participants"]

    def test_diamond_dag(self):
        """
        A -> B, A -> C, B -> D, C -> D
        D should have parents [B, C] (or [C, B] depending on sort).
        """
        shape = [
            _make_shape_item("s1", "get_recording", children_step_ids=["s2", "s3"]),
            _make_shape_item("s2", "mixdown_tracks", children_step_ids=["s4"]),
            _make_shape_item("s3", "detect_topics", children_step_ids=["s4"]),
            _make_shape_item("s4", "finalize"),
        ]
        tasks = [
            _make_task_summary("s1", status="COMPLETED"),
            _make_task_summary("s2", status="RUNNING"),
            _make_task_summary("s3", status="RUNNING"),
            _make_task_summary("s4", status="QUEUED"),
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        # Topological: s1 first, s2/s3 in some order, s4 last
        assert result[0].name == "get_recording"
        assert result[-1].name == "finalize"
        finalize = result[-1]
        assert set(finalize.parents) == {"mixdown_tracks", "detect_topics"}

    def test_topological_order_is_stable(self):
        """Verify deterministic ordering (sorted queue in Kahn's)."""
        shape = [
            _make_shape_item("s_c", "task_c"),
            _make_shape_item("s_a", "task_a", children_step_ids=["s_c"]),
            _make_shape_item("s_b", "task_b", children_step_ids=["s_c"]),
        ]
        tasks = [
            _make_task_summary("s_c", status="QUEUED"),
            _make_task_summary("s_a", status="COMPLETED"),
            _make_task_summary("s_b", status="COMPLETED"),
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        # s_a and s_b both roots with in-degree 0; sorted alphabetically by step_id
        names = [t.name for t in result]
        assert names[-1] == "task_c"
        # First two should be task_a, task_b (sorted by step_id: s_a < s_b)
        assert names[0] == "task_a"
        assert names[1] == "task_b"

    def test_production_dag_shape(self):
        """Test the real 15-task pipeline topology with mixed statuses.

        Simulates a mid-pipeline state where early tasks completed,
        middle tasks running, and later tasks still queued.
        """
        # Production DAG edges (parent -> children):
        # get_recording -> get_participants
        # get_participants -> process_tracks
        # process_tracks -> mixdown_tracks, detect_topics, finalize
        # mixdown_tracks -> generate_waveform
        # detect_topics -> generate_title, extract_subjects
        # extract_subjects -> process_subjects, identify_action_items
        # process_subjects -> generate_recap
        # generate_title -> finalize
        # generate_recap -> finalize
        # identify_action_items -> finalize
        # finalize -> cleanup_consent
        # cleanup_consent -> post_zulip, send_webhook
        shape = [
            _make_shape_item(
                "s_get_recording", TaskName.GET_RECORDING, ["s_get_participants"]
            ),
            _make_shape_item(
                "s_get_participants", TaskName.GET_PARTICIPANTS, ["s_process_tracks"]
            ),
            _make_shape_item(
                "s_process_tracks",
                TaskName.PROCESS_TRACKS,
                ["s_mixdown_tracks", "s_detect_topics", "s_finalize"],
            ),
            _make_shape_item(
                "s_mixdown_tracks", TaskName.MIXDOWN_TRACKS, ["s_generate_waveform"]
            ),
            _make_shape_item("s_generate_waveform", TaskName.GENERATE_WAVEFORM),
            _make_shape_item(
                "s_detect_topics",
                TaskName.DETECT_TOPICS,
                ["s_generate_title", "s_extract_subjects"],
            ),
            _make_shape_item(
                "s_generate_title", TaskName.GENERATE_TITLE, ["s_finalize"]
            ),
            _make_shape_item(
                "s_extract_subjects",
                TaskName.EXTRACT_SUBJECTS,
                ["s_process_subjects", "s_identify_action_items"],
            ),
            _make_shape_item(
                "s_process_subjects", TaskName.PROCESS_SUBJECTS, ["s_generate_recap"]
            ),
            _make_shape_item(
                "s_generate_recap", TaskName.GENERATE_RECAP, ["s_finalize"]
            ),
            _make_shape_item(
                "s_identify_action_items",
                TaskName.IDENTIFY_ACTION_ITEMS,
                ["s_finalize"],
            ),
            _make_shape_item("s_finalize", TaskName.FINALIZE, ["s_cleanup_consent"]),
            _make_shape_item(
                "s_cleanup_consent",
                TaskName.CLEANUP_CONSENT,
                ["s_post_zulip", "s_send_webhook"],
            ),
            _make_shape_item("s_post_zulip", TaskName.POST_ZULIP),
            _make_shape_item("s_send_webhook", TaskName.SEND_WEBHOOK),
        ]

        # Mid-pipeline: early tasks done, middle running, later queued
        tasks = [
            _make_task_summary("s_get_recording", status="COMPLETED"),
            _make_task_summary("s_get_participants", status="COMPLETED"),
            _make_task_summary("s_process_tracks", status="COMPLETED"),
            _make_task_summary("s_mixdown_tracks", status="RUNNING"),
            _make_task_summary("s_generate_waveform", status="QUEUED"),
            _make_task_summary("s_detect_topics", status="RUNNING"),
            _make_task_summary("s_generate_title", status="QUEUED"),
            _make_task_summary("s_extract_subjects", status="QUEUED"),
            _make_task_summary("s_process_subjects", status="QUEUED"),
            _make_task_summary("s_generate_recap", status="QUEUED"),
            _make_task_summary("s_identify_action_items", status="QUEUED"),
            _make_task_summary("s_finalize", status="QUEUED"),
            _make_task_summary("s_cleanup_consent", status="QUEUED"),
            _make_task_summary("s_post_zulip", status="QUEUED"),
            _make_task_summary("s_send_webhook", status="QUEUED"),
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        # All 15 tasks present
        assert len(result) == 15
        result_names = [t.name for t in result]
        assert set(result_names) == {
            TaskName.GET_RECORDING,
            TaskName.GET_PARTICIPANTS,
            TaskName.PROCESS_TRACKS,
            TaskName.MIXDOWN_TRACKS,
            TaskName.GENERATE_WAVEFORM,
            TaskName.DETECT_TOPICS,
            TaskName.GENERATE_TITLE,
            TaskName.EXTRACT_SUBJECTS,
            TaskName.PROCESS_SUBJECTS,
            TaskName.GENERATE_RECAP,
            TaskName.IDENTIFY_ACTION_ITEMS,
            TaskName.FINALIZE,
            TaskName.CLEANUP_CONSENT,
            TaskName.POST_ZULIP,
            TaskName.SEND_WEBHOOK,
        }

        # Topological order invariant: no task appears before its parents
        name_to_index = {t.name: i for i, t in enumerate(result)}
        for task in result:
            for parent_name in task.parents:
                assert name_to_index[parent_name] < name_to_index[task.name], (
                    f"Parent {parent_name} (idx {name_to_index[parent_name]}) "
                    f"must appear before {task.name} (idx {name_to_index[task.name]})"
                )

        # finalize has exactly 4 parents
        finalize = next(t for t in result if t.name == TaskName.FINALIZE)
        assert set(finalize.parents) == {
            TaskName.PROCESS_TRACKS,
            TaskName.GENERATE_TITLE,
            TaskName.GENERATE_RECAP,
            TaskName.IDENTIFY_ACTION_ITEMS,
        }

        # cleanup_consent has 1 parent (finalize)
        cleanup = next(t for t in result if t.name == TaskName.CLEANUP_CONSENT)
        assert cleanup.parents == [TaskName.FINALIZE]

        # post_zulip and send_webhook both have cleanup_consent as parent
        post_zulip = next(t for t in result if t.name == TaskName.POST_ZULIP)
        send_webhook = next(t for t in result if t.name == TaskName.SEND_WEBHOOK)
        assert post_zulip.parents == [TaskName.CLEANUP_CONSENT]
        assert send_webhook.parents == [TaskName.CLEANUP_CONSENT]

        # Verify statuses propagated correctly
        assert (
            next(t for t in result if t.name == TaskName.GET_RECORDING).status
            == DagTaskStatus.COMPLETED
        )
        assert (
            next(t for t in result if t.name == TaskName.MIXDOWN_TRACKS).status
            == DagTaskStatus.RUNNING
        )
        assert (
            next(t for t in result if t.name == TaskName.FINALIZE).status
            == DagTaskStatus.QUEUED
        )

    def test_topological_sort_invariant_complex_dag(self):
        """For a complex DAG, every task's parents appear earlier in the list.

        Uses a wider branching/merging DAG than diamond to stress the invariant.
        """
        # DAG: A -> B, A -> C, A -> D, B -> E, C -> E, C -> F, D -> F, E -> G, F -> G
        shape = [
            _make_shape_item("s_a", "task_a", ["s_b", "s_c", "s_d"]),
            _make_shape_item("s_b", "task_b", ["s_e"]),
            _make_shape_item("s_c", "task_c", ["s_e", "s_f"]),
            _make_shape_item("s_d", "task_d", ["s_f"]),
            _make_shape_item("s_e", "task_e", ["s_g"]),
            _make_shape_item("s_f", "task_f", ["s_g"]),
            _make_shape_item("s_g", "task_g"),
        ]
        tasks = [
            _make_task_summary("s_a", status="COMPLETED"),
            _make_task_summary("s_b", status="COMPLETED"),
            _make_task_summary("s_c", status="RUNNING"),
            _make_task_summary("s_d", status="COMPLETED"),
            _make_task_summary("s_e", status="QUEUED"),
            _make_task_summary("s_f", status="QUEUED"),
            _make_task_summary("s_g", status="QUEUED"),
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert len(result) == 7
        name_to_index = {t.name: i for i, t in enumerate(result)}

        # Verify invariant: every parent appears before its child
        for task in result:
            for parent_name in task.parents:
                assert name_to_index[parent_name] < name_to_index[task.name], (
                    f"Parent {parent_name} (idx {name_to_index[parent_name]}) "
                    f"must appear before {task.name} (idx {name_to_index[task.name]})"
                )

        # task_g has 2 parents
        task_g = next(t for t in result if t.name == "task_g")
        assert set(task_g.parents) == {"task_e", "task_f"}

        # task_e has 2 parents
        task_e = next(t for t in result if t.name == "task_e")
        assert set(task_e.parents) == {"task_b", "task_c"}

        # task_a is root (first in topological order)
        assert result[0].name == "task_a"
        assert result[0].parents == []


class TestExtractDagTasksFanOut:
    """Test fan-out tasks with spawned children."""

    def test_fan_out_children_counts(self):
        from hatchet_sdk.clients.rest.models import V1TaskStatus

        child_mocks = []
        for status in ["COMPLETED", "COMPLETED", "RUNNING", "QUEUED"]:
            child = MagicMock()
            child.status = V1TaskStatus(status)
            child_mocks.append(child)

        shape = [_make_shape_item("s1", "process_tracks")]
        tasks = [
            _make_task_summary(
                "s1",
                status="RUNNING",
                num_spawned_children=4,
                children=child_mocks,
            )
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].children_total == 4
        assert result[0].children_completed == 2

    def test_no_children_when_no_spawn(self):
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = [
            _make_task_summary("s1", status="COMPLETED", num_spawned_children=None)
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].children_total is None
        assert result[0].children_completed is None

    def test_zero_spawned_children(self):
        shape = [_make_shape_item("s1", "process_tracks")]
        tasks = [_make_task_summary("s1", status="COMPLETED", num_spawned_children=0)]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert result[0].children_total is None
        assert result[0].children_completed is None


class TestExtractDagTasksErrorExtraction:
    """Test error message extraction logic."""

    def test_simple_error(self):
        shape = [_make_shape_item("s1", "mixdown_tracks")]
        tasks = [
            _make_task_summary(
                "s1", status="FAILED", error_message="ValueError: no tracks"
            )
        ]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)
        assert result[0].error == "ValueError: no tracks"

    def test_traceback_extracts_meaningful_line(self):
        error = (
            "Traceback (most recent call last):\n"
            '  File "/app/something.py", line 42\n'
            "RuntimeError: out of memory"
        )
        shape = [_make_shape_item("s1", "mixdown_tracks")]
        tasks = [_make_task_summary("s1", status="FAILED", error_message=error)]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)
        assert result[0].error == "RuntimeError: out of memory"

    def test_no_error_when_none(self):
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = [_make_task_summary("s1", status="COMPLETED", error_message=None)]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)
        assert result[0].error is None

    def test_empty_error_message(self):
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = [_make_task_summary("s1", status="FAILED", error_message="")]
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)
        assert result[0].error is None


class TestExtractDagTasksMissingData:
    """Test edge cases with missing task data."""

    def test_shape_without_matching_task(self):
        """Shape has a step but tasks list doesn't contain it."""
        shape = [_make_shape_item("s1", "get_recording")]
        tasks = []  # No matching task
        details = _make_details(shape, tasks)

        result = extract_dag_tasks(details)

        assert len(result) == 1
        assert result[0].name == "get_recording"
        assert result[0].status == DagTaskStatus.QUEUED  # default when no task data
        assert result[0].started_at is None

    def test_none_shape_returns_empty(self):
        details = _make_details(shape=[], tasks=[])
        details.shape = None

        result = extract_dag_tasks(details)
        assert result == []


class TestDagStatusData:
    """Test DagStatusData model serialization."""

    def test_serialization(self):
        task = DagTask(
            name="get_recording",
            status=DagTaskStatus.COMPLETED,
            started_at=datetime(2025, 1, 1, tzinfo=timezone.utc),
            finished_at=datetime(2025, 1, 1, 0, 0, 1, tzinfo=timezone.utc),
            duration_seconds=1.0,
            parents=[],
            error=None,
            children_total=None,
            children_completed=None,
            progress_pct=None,
        )
        data = DagStatusData(workflow_run_id="test-123", tasks=[task])
        dumped = data.model_dump(mode="json")

        assert dumped["workflow_run_id"] == "test-123"
        assert len(dumped["tasks"]) == 1
        assert dumped["tasks"][0]["name"] == "get_recording"
        assert dumped["tasks"][0]["status"] == "completed"
        assert dumped["tasks"][0]["duration_seconds"] == 1.0


class AsyncContextManager:
    """No-op async context manager for mocking fresh_db_connection."""

    async def __aenter__(self):
        return None

    async def __aexit__(self, *args):
        return None


class TestBroadcastDagStatus:
    """Test broadcast_dag_status function.

    broadcast_dag_status uses deferred imports inside its function body.
    We mock the source modules/objects before calling the function.
    Importing daily_multitrack_pipeline triggers a cascade
    (subject_processing -> HatchetClientManager.get_client at module level),
    so we set _instance before the import to prevent real SDK init.
    """

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

    @pytest.mark.asyncio
    async def test_broadcasts_dag_status(self):
        """broadcast_dag_status fetches run, transforms, and broadcasts."""
        mock_transcript = MagicMock()
        mock_transcript.id = "t-123"

        mock_details = _make_details(
            shape=[_make_shape_item("s1", "get_recording")],
            tasks=[_make_task_summary("s1", status="COMPLETED")],
            run_id="wf-abc",
        )

        mock_client = MagicMock()
        mock_client.runs.aio_get = AsyncMock(return_value=mock_details)

        with (
            patch(
                "reflector.hatchet.client.HatchetClientManager.get_client",
                return_value=mock_client,
            ),
            patch(
                "reflector.hatchet.broadcast.append_event_and_broadcast",
                new_callable=AsyncMock,
            ) as mock_broadcast,
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=mock_transcript,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.fresh_db_connection",
                return_value=AsyncContextManager(),
            ),
        ):
            from reflector.hatchet.dag_progress import broadcast_dag_status

            await broadcast_dag_status("t-123", "wf-abc")

            mock_client.runs.aio_get.assert_called_once_with("wf-abc")
            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[0][0] == "t-123"  # transcript_id
            assert call_args[0][1] is mock_transcript  # transcript
            assert call_args[0][2] == "DAG_STATUS"  # event_name
            data = call_args[0][3]
            assert isinstance(data, DagStatusData)
            assert data.workflow_run_id == "wf-abc"
            assert len(data.tasks) == 1

    @pytest.mark.asyncio
    async def test_swallows_exceptions(self):
        """broadcast_dag_status never raises even when internals fail."""
        from reflector.hatchet.dag_progress import broadcast_dag_status

        with patch(
            "reflector.hatchet.workflows.daily_multitrack_pipeline.fresh_db_connection",
            side_effect=RuntimeError("db exploded"),
        ):
            # Should not raise
            await broadcast_dag_status("t-123", "wf-abc")

    @pytest.mark.asyncio
    async def test_no_broadcast_when_transcript_not_found(self):
        """broadcast_dag_status does not broadcast if transcript is None."""
        mock_details = _make_details(
            shape=[_make_shape_item("s1", "get_recording")],
            tasks=[_make_task_summary("s1", status="COMPLETED")],
        )

        mock_client = MagicMock()
        mock_client.runs.aio_get = AsyncMock(return_value=mock_details)

        with (
            patch(
                "reflector.hatchet.client.HatchetClientManager.get_client",
                return_value=mock_client,
            ),
            patch(
                "reflector.hatchet.workflows.daily_multitrack_pipeline.fresh_db_connection",
                return_value=AsyncContextManager(),
            ),
            patch(
                "reflector.db.transcripts.transcripts_controller.get_by_id",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "reflector.hatchet.broadcast.append_event_and_broadcast",
                new_callable=AsyncMock,
            ) as mock_broadcast,
        ):
            from reflector.hatchet.dag_progress import broadcast_dag_status

            await broadcast_dag_status("t-123", "wf-abc")

            mock_broadcast.assert_not_called()


class TestMakeAudioProgressLoggerWithBroadcast:
    """Test make_audio_progress_logger with transcript_id for transient broadcasts."""

    @pytest.fixture(autouse=True)
    def _setup_hatchet_mock(self):
        """Set HatchetClientManager._instance to prevent real SDK init on import."""
        from reflector.hatchet.client import HatchetClientManager

        original = HatchetClientManager._instance
        if original is None:
            HatchetClientManager._instance = MagicMock()
        yield
        HatchetClientManager._instance = original

    def test_broadcasts_transient_progress_event(self):
        """When transcript_id provided and progress_pct not None, broadcasts event."""
        import asyncio

        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            make_audio_progress_logger,
        )

        ctx = MagicMock()
        ctx.log = MagicMock()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        mock_broadcast = AsyncMock()
        tasks_created = []

        original_create_task = loop.create_task

        def capture_create_task(coro):
            task = original_create_task(coro)
            tasks_created.append(task)
            return task

        try:
            with (
                patch(
                    "reflector.hatchet.broadcast.broadcast_event",
                    mock_broadcast,
                ),
                patch.object(loop, "create_task", side_effect=capture_create_task),
            ):
                callback = make_audio_progress_logger(
                    ctx, TaskName.MIXDOWN_TRACKS, interval=0.0, transcript_id="t-123"
                )
                callback(50.0, 100.0)

                # Run pending tasks
                if tasks_created:
                    loop.run_until_complete(asyncio.gather(*tasks_created))

                mock_broadcast.assert_called_once()
                event_arg = mock_broadcast.call_args[0][1]
                assert event_arg.event == "DAG_TASK_PROGRESS"
                assert event_arg.data["task_name"] == TaskName.MIXDOWN_TRACKS
                assert event_arg.data["progress_pct"] == 50.0
        finally:
            loop.close()

    def test_no_broadcast_without_transcript_id(self):
        """When transcript_id is None, no broadcast happens."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            make_audio_progress_logger,
        )

        ctx = MagicMock()

        with patch(
            "reflector.hatchet.broadcast.broadcast_event",
            new_callable=AsyncMock,
        ) as mock_broadcast:
            callback = make_audio_progress_logger(
                ctx, TaskName.MIXDOWN_TRACKS, interval=0.0, transcript_id=None
            )
            callback(50.0, 100.0)
            mock_broadcast.assert_not_called()

    def test_no_broadcast_when_progress_pct_is_none(self):
        """When progress_pct is None, no broadcast happens even with transcript_id."""
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            make_audio_progress_logger,
        )

        ctx = MagicMock()

        with patch(
            "reflector.hatchet.broadcast.broadcast_event",
            new_callable=AsyncMock,
        ) as mock_broadcast:
            callback = make_audio_progress_logger(
                ctx, TaskName.MIXDOWN_TRACKS, interval=0.0, transcript_id="t-123"
            )
            callback(None, 100.0)
            mock_broadcast.assert_not_called()

    def test_logging_throttled_by_interval(self):
        """With interval=5.0, rapid calls only log once until interval elapses.

        The throttle applies to ctx.log() calls. Broadcasts (fire-and-forget)
        are not throttled — they occur every call when transcript_id + progress_pct set.
        """
        import asyncio
        import time as time_mod

        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            make_audio_progress_logger,
        )

        ctx = MagicMock()
        ctx.log = MagicMock()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        mock_broadcast = AsyncMock()
        tasks_created = []
        original_create_task = loop.create_task

        def capture_create_task(coro):
            task = original_create_task(coro)
            tasks_created.append(task)
            return task

        # Controlled monotonic values for the 4 calls from make_audio_progress_logger:
        # init (start_time, last_log_time), call1 (now), call2 (now), call3 (now)
        # After those, fall back to real time.monotonic() for asyncio internals.
        controlled_values = [100.0, 100.0, 101.0, 106.0]
        call_index = [0]
        real_monotonic = time_mod.monotonic

        def mock_monotonic():
            if call_index[0] < len(controlled_values):
                val = controlled_values[call_index[0]]
                call_index[0] += 1
                return val
            return real_monotonic()

        try:
            with (
                patch(
                    "reflector.hatchet.workflows.daily_multitrack_pipeline.time.monotonic",
                    side_effect=mock_monotonic,
                ),
                patch(
                    "reflector.hatchet.broadcast.broadcast_event",
                    mock_broadcast,
                ),
                patch.object(loop, "create_task", side_effect=capture_create_task),
            ):
                callback = make_audio_progress_logger(
                    ctx, TaskName.MIXDOWN_TRACKS, interval=5.0, transcript_id="t-123"
                )

                # Call 1 at t=100.0: 100.0 - 100.0 = 0.0 < 5.0 => no log
                callback(25.0, 50.0)
                assert ctx.log.call_count == 0

                # Call 2 at t=101.0: 101.0 - 100.0 = 1.0 < 5.0 => no log
                callback(50.0, 100.0)
                assert ctx.log.call_count == 0

                # Call 3 at t=106.0: 106.0 - 100.0 = 6.0 >= 5.0 => logs
                callback(75.0, 150.0)
                assert ctx.log.call_count == 1

                # Run pending broadcast tasks
                if tasks_created:
                    loop.run_until_complete(asyncio.gather(*tasks_created))

                # Broadcasts happen on every call (not throttled) — 3 calls total
                assert mock_broadcast.call_count == 3
        finally:
            loop.close()

    def test_uses_broadcast_event_not_append_event_and_broadcast(self):
        """Progress events use broadcast_event (transient), not append_event_and_broadcast (persisted)."""
        import asyncio

        from reflector.hatchet.workflows.daily_multitrack_pipeline import (
            make_audio_progress_logger,
        )

        ctx = MagicMock()
        ctx.log = MagicMock()

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        mock_broadcast_event = AsyncMock()
        mock_append = AsyncMock()
        tasks_created = []
        original_create_task = loop.create_task

        def capture_create_task(coro):
            task = original_create_task(coro)
            tasks_created.append(task)
            return task

        try:
            with (
                patch(
                    "reflector.hatchet.broadcast.broadcast_event",
                    mock_broadcast_event,
                ),
                patch(
                    "reflector.hatchet.broadcast.append_event_and_broadcast",
                    mock_append,
                ),
                patch.object(loop, "create_task", side_effect=capture_create_task),
            ):
                callback = make_audio_progress_logger(
                    ctx, TaskName.MIXDOWN_TRACKS, interval=0.0, transcript_id="t-123"
                )
                callback(50.0, 100.0)

                if tasks_created:
                    loop.run_until_complete(asyncio.gather(*tasks_created))

                # broadcast_event (transient) IS called
                mock_broadcast_event.assert_called_once()
                # append_event_and_broadcast (persisted) is NOT called
                mock_append.assert_not_called()
        finally:
            loop.close()
