"""
DAG Progress Reporting — models and transform.

Converts Hatchet V1WorkflowRunDetails into structured DagTask list
for frontend WebSocket/REST consumption.

Ported from render_hatchet_run.py (feat-dag-zulip) which renders markdown;
this module produces structured Pydantic models instead.
"""

from datetime import datetime
from enum import StrEnum

from hatchet_sdk.clients.rest.models import (
    V1TaskStatus,
    V1WorkflowRunDetails,
    WorkflowRunShapeItemForWorkflowRunDetails,
)
from pydantic import BaseModel


class DagTaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


_HATCHET_TO_DAG_STATUS: dict[V1TaskStatus, DagTaskStatus] = {
    V1TaskStatus.QUEUED: DagTaskStatus.QUEUED,
    V1TaskStatus.RUNNING: DagTaskStatus.RUNNING,
    V1TaskStatus.COMPLETED: DagTaskStatus.COMPLETED,
    V1TaskStatus.FAILED: DagTaskStatus.FAILED,
    V1TaskStatus.CANCELLED: DagTaskStatus.CANCELLED,
}


class DagTask(BaseModel):
    name: str
    status: DagTaskStatus
    started_at: datetime | None
    finished_at: datetime | None
    duration_seconds: float | None
    parents: list[str]
    error: str | None
    children_total: int | None
    children_completed: int | None
    progress_pct: float | None


class DagStatusData(BaseModel):
    workflow_run_id: str
    tasks: list[DagTask]


def _topo_sort(
    shape: list[WorkflowRunShapeItemForWorkflowRunDetails],
) -> list[str]:
    """Topological sort of step_ids from shape DAG (Kahn's algorithm).

    Ported from render_hatchet_run.py.
    """
    step_ids = {s.step_id for s in shape}
    children_map: dict[str, list[str]] = {}
    in_degree: dict[str, int] = {sid: 0 for sid in step_ids}

    for s in shape:
        children = [c for c in (s.children_step_ids or []) if c in step_ids]
        children_map[s.step_id] = children
        for c in children:
            in_degree[c] += 1

    queue = sorted(sid for sid, deg in in_degree.items() if deg == 0)
    result: list[str] = []
    while queue:
        node = queue.pop(0)
        result.append(node)
        for c in children_map.get(node, []):
            in_degree[c] -= 1
            if in_degree[c] == 0:
                queue.append(c)
                queue.sort()

    return result


def _extract_error_summary(error_message: str | None) -> str | None:
    """Extract first meaningful line from error message, skipping traceback frames."""
    if not error_message or not error_message.strip():
        return None

    err_lines = error_message.strip().split("\n")
    err_summary = err_lines[0]
    for line in err_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(("Traceback", "File ", "{", ")")):
            err_summary = stripped
    return err_summary


def extract_dag_tasks(details: V1WorkflowRunDetails) -> list[DagTask]:
    """Extract structured DagTask list from Hatchet workflow run details.

    Returns tasks in topological order with status, timestamps, parents,
    error summaries, and fan-out children counts.
    """
    shape = details.shape or []
    tasks = details.tasks or []

    if not shape:
        return []

    # Build lookups
    step_to_shape: dict[str, WorkflowRunShapeItemForWorkflowRunDetails] = {
        s.step_id: s for s in shape
    }
    step_to_name: dict[str, str] = {s.step_id: s.task_name for s in shape}

    # Reverse edges: child -> parent names
    parents_by_step: dict[str, list[str]] = {s.step_id: [] for s in shape}
    for s in shape:
        for child_id in s.children_step_ids or []:
            if child_id in parents_by_step:
                parents_by_step[child_id].append(step_to_name[s.step_id])

    # Join tasks by step_id
    from hatchet_sdk.clients.rest.models import V1TaskSummary  # noqa: PLC0415

    task_by_step: dict[str, V1TaskSummary] = {}
    for t in tasks:
        if t.step_id and t.step_id in step_to_name:
            task_by_step[t.step_id] = t

    ordered = _topo_sort(shape)

    result: list[DagTask] = []
    for step_id in ordered:
        name = step_to_name[step_id]
        t = task_by_step.get(step_id)

        if not t:
            result.append(
                DagTask(
                    name=name,
                    status=DagTaskStatus.QUEUED,
                    started_at=None,
                    finished_at=None,
                    duration_seconds=None,
                    parents=parents_by_step.get(step_id, []),
                    error=None,
                    children_total=None,
                    children_completed=None,
                    progress_pct=None,
                )
            )
            continue

        status = _HATCHET_TO_DAG_STATUS.get(t.status, DagTaskStatus.QUEUED)

        duration_seconds: float | None = None
        if t.duration is not None:
            duration_seconds = t.duration / 1000.0

        # Fan-out children
        children_total: int | None = None
        children_completed: int | None = None
        if t.num_spawned_children and t.num_spawned_children > 0:
            children_total = t.num_spawned_children
            children_completed = sum(
                1 for c in (t.children or []) if c.status == V1TaskStatus.COMPLETED
            )

        result.append(
            DagTask(
                name=name,
                status=status,
                started_at=t.started_at,
                finished_at=t.finished_at,
                duration_seconds=duration_seconds,
                parents=parents_by_step.get(step_id, []),
                error=_extract_error_summary(t.error_message),
                children_total=children_total,
                children_completed=children_completed,
                progress_pct=None,
            )
        )

    return result


async def broadcast_dag_status(transcript_id: str, workflow_run_id: str) -> None:
    """Fetch current DAG state from Hatchet and broadcast via WebSocket.

    Fire-and-forget: exceptions are logged but never raised.
    All imports are deferred for fork-safety (Hatchet workers fork processes).
    """
    try:
        from reflector.db.transcripts import transcripts_controller  # noqa: I001, PLC0415
        from reflector.hatchet.broadcast import append_event_and_broadcast  # noqa: PLC0415
        from reflector.hatchet.client import HatchetClientManager  # noqa: PLC0415
        from reflector.hatchet.workflows.daily_multitrack_pipeline import (  # noqa: PLC0415
            fresh_db_connection,
        )
        from reflector.logger import logger  # noqa: PLC0415

        async with fresh_db_connection():
            client = HatchetClientManager.get_client()
            details = await client.runs.aio_get(workflow_run_id)
            dag_tasks = extract_dag_tasks(details)
            dag_status = DagStatusData(workflow_run_id=workflow_run_id, tasks=dag_tasks)

            transcript = await transcripts_controller.get_by_id(transcript_id)
            if transcript:
                await append_event_and_broadcast(
                    transcript_id,
                    transcript,
                    "DAG_STATUS",
                    dag_status.model_dump(mode="json"),
                    logger,
                )
    except Exception:
        from reflector.logger import logger  # noqa: PLC0415

        logger.warning(
            "[DAG Progress] Failed to broadcast DAG status",
            transcript_id=transcript_id,
            workflow_run_id=workflow_run_id,
            exc_info=True,
        )
