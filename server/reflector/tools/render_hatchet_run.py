"""
Render Hatchet workflow runs as text DAG.

Usage:
    # Show latest 5 runs (summary table)
    uv run -m reflector.tools.render_hatchet_run

    # Show specific run with full DAG + task details
    uv run -m reflector.tools.render_hatchet_run <workflow_run_id>

    # Drill into Nth run from the list (1-indexed)
    uv run -m reflector.tools.render_hatchet_run --show 1

    # Show latest N runs
    uv run -m reflector.tools.render_hatchet_run --last 10

    # Filter by status
    uv run -m reflector.tools.render_hatchet_run --status FAILED
    uv run -m reflector.tools.render_hatchet_run --status RUNNING
"""

import argparse
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from hatchet_sdk.clients.rest.models import (
    V1TaskEvent,
    V1TaskStatus,
    V1TaskSummary,
    V1WorkflowRunDetails,
    WorkflowRunShapeItemForWorkflowRunDetails,
)

from reflector.hatchet.client import HatchetClientManager

STATUS_ICON = {
    V1TaskStatus.COMPLETED: "\u2705",
    V1TaskStatus.RUNNING: "\u23f3",
    V1TaskStatus.FAILED: "\u274c",
    V1TaskStatus.QUEUED: "\u23f8\ufe0f",
    V1TaskStatus.CANCELLED: "\u26a0\ufe0f",
}

STATUS_LABEL = {
    V1TaskStatus.COMPLETED: "Complete",
    V1TaskStatus.RUNNING: "Running",
    V1TaskStatus.FAILED: "FAILED",
    V1TaskStatus.QUEUED: "Queued",
    V1TaskStatus.CANCELLED: "Cancelled",
}


def _fmt_time(dt: datetime | None) -> str:
    if dt is None:
        return "-"
    return dt.strftime("%H:%M:%S")


def _fmt_duration(ms: int | None) -> str:
    if ms is None:
        return "-"
    secs = ms / 1000
    if secs < 60:
        return f"{secs:.1f}s"
    mins = secs / 60
    return f"{mins:.1f}m"


def _fmt_status_line(task: V1TaskSummary) -> str:
    """Format a status line like: Complete (finished 20:31:44)"""
    label = STATUS_LABEL.get(task.status, task.status.value)
    icon = STATUS_ICON.get(task.status, "?")

    if task.status == V1TaskStatus.COMPLETED and task.finished_at:
        return f"{icon} {label} (finished {_fmt_time(task.finished_at)})"
    elif task.status == V1TaskStatus.RUNNING and task.started_at:
        parts = [f"started {_fmt_time(task.started_at)}"]
        if task.duration:
            parts.append(f"{_fmt_duration(task.duration)} elapsed")
        return f"{icon} {label} ({', '.join(parts)})"
    elif task.status == V1TaskStatus.FAILED and task.finished_at:
        return f"{icon} {label} (failed {_fmt_time(task.finished_at)})"
    elif task.status == V1TaskStatus.CANCELLED:
        return f"{icon} {label}"
    elif task.status == V1TaskStatus.QUEUED:
        return f"{icon} {label}"
    return f"{icon} {label}"


def _topo_sort(
    shape: list[WorkflowRunShapeItemForWorkflowRunDetails],
) -> list[str]:
    """Topological sort of step_ids from shape DAG."""
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


def render_run_detail(details: V1WorkflowRunDetails) -> str:
    """Render a single workflow run as markdown DAG with task details."""
    shape = details.shape or []
    tasks = details.tasks or []
    events = details.task_events or []
    run = details.run

    if not shape:
        return f"Run {run.metadata.id}: {run.status.value} (no shape data)"

    # Build lookups
    step_to_shape: dict[str, WorkflowRunShapeItemForWorkflowRunDetails] = {
        s.step_id: s for s in shape
    }
    step_to_name: dict[str, str] = {s.step_id: s.task_name for s in shape}

    # Reverse edges (parents)
    parents: dict[str, list[str]] = {s.step_id: [] for s in shape}
    for s in shape:
        for child_id in s.children_step_ids or []:
            if child_id in parents:
                parents[child_id].append(s.step_id)

    # Join tasks by step_id
    task_by_step: dict[str, V1TaskSummary] = {}
    for t in tasks:
        if t.step_id and t.step_id in step_to_name:
            task_by_step[t.step_id] = t

    # Events indexed by task_external_id
    events_by_task: dict[str, list[V1TaskEvent]] = defaultdict(list)
    for ev in events:
        events_by_task[ev.task_id].append(ev)

    ordered = _topo_sort(shape)

    lines: list[str] = []

    # Run header
    run_icon = STATUS_ICON.get(run.status, "?")
    run_name = run.display_name or run.workflow_id
    dur = _fmt_duration(run.duration)
    lines.append(f"**{run_name}** {run_icon} {dur}")
    lines.append(f"ID: `{run.metadata.id}`")
    if run.additional_metadata:
        meta_parts = [f"{k}=`{v}`" for k, v in run.additional_metadata.items()]
        lines.append(f"Meta: {', '.join(meta_parts)}")
    if run.error_message:
        # Take first line of error only for header
        first_line = run.error_message.split("\n")[0]
        lines.append(f"Error: {first_line}")
    lines.append("")

    # DAG Status Overview table
    lines.append("**DAG Status Overview**")
    lines.append("")
    lines.append("| Node | Status | Duration | Dependencies |")
    lines.append("|------|--------|----------|--------------|")

    for step_id in ordered:
        s = step_to_shape[step_id]
        t = task_by_step.get(step_id)
        name = step_to_name[step_id]
        icon = STATUS_ICON.get(t.status, "?") if t else "?"
        dur = _fmt_duration(t.duration) if t else "-"

        parent_names = [step_to_name[p] for p in parents[step_id]]
        child_names = [
            step_to_name[c] for c in (s.children_step_ids or []) if c in step_to_name
        ]
        deps_left = ", ".join(parent_names) if parent_names else ""
        deps_right = ", ".join(child_names) if child_names else ""
        if deps_left and deps_right:
            deps = f"{deps_left} \u2192 {deps_right}"
        elif deps_right:
            deps = f"\u2192 {deps_right}"
        elif deps_left:
            deps = f"{deps_left} \u2192"
        else:
            deps = "-"

        lines.append(f"| {name} | {icon} | {dur} | {deps} |")

    lines.append("")
    lines.append("---")
    lines.append("")

    # Node details
    for step_id in ordered:
        t = task_by_step.get(step_id)
        name = step_to_name[step_id]

        if not t:
            lines.append(f"**\U0001f4e6 {name}**")
            lines.append("Status: no task data")
            lines.append("")
            continue

        lines.append(f"**\U0001f4e6 {name}**")
        lines.append(f"Status: {_fmt_status_line(t)}")

        if t.duration:
            lines.append(f"Duration: {_fmt_duration(t.duration)}")
        if t.retry_count and t.retry_count > 0:
            lines.append(f"Retries: {t.retry_count}")

        # Fan-out children
        if t.num_spawned_children and t.num_spawned_children > 0:
            children = t.children or []
            completed = sum(1 for c in children if c.status == V1TaskStatus.COMPLETED)
            failed = sum(1 for c in children if c.status == V1TaskStatus.FAILED)
            running = sum(1 for c in children if c.status == V1TaskStatus.RUNNING)
            lines.append(
                f"Spawned children: {completed}/{t.num_spawned_children} done"
                f"{f', {running} running' if running else ''}"
                f"{f', {failed} failed' if failed else ''}"
            )

        # Error message (first meaningful line only, full trace in events)
        if t.error_message:
            err_lines = t.error_message.strip().split("\n")
            # Find first non-empty, non-traceback line
            err_summary = err_lines[0]
            for line in err_lines:
                stripped = line.strip()
                if stripped and not stripped.startswith(
                    ("Traceback", "File ", "{", ")")
                ):
                    err_summary = stripped
                    break
            lines.append(f"Error: `{err_summary}`")

        # Events log
        task_events = sorted(
            events_by_task.get(t.task_external_id, []),
            key=lambda e: e.timestamp,
        )
        if task_events:
            lines.append("Events:")
            for ev in task_events:
                ts = ev.timestamp.strftime("%H:%M:%S")
                ev_icon = ""
                if ev.event_type.value == "FINISHED":
                    ev_icon = "\u2705 "
                elif ev.event_type.value in ("FAILED", "TIMED_OUT"):
                    ev_icon = "\u274c "
                elif ev.event_type.value == "STARTED":
                    ev_icon = "\u25b6\ufe0f "
                elif ev.event_type.value == "RETRYING":
                    ev_icon = "\U0001f504 "
                elif ev.event_type.value == "CANCELLED":
                    ev_icon = "\u26a0\ufe0f "

                msg = ev.message.strip()
                if ev.error_message:
                    # Just first line of error in event log
                    err_first = ev.error_message.strip().split("\n")[0]
                    if msg:
                        msg += f" | {err_first}"
                    else:
                        msg = err_first

                if msg:
                    lines.append(f"  `{ts}` {ev_icon}{ev.event_type.value}: {msg}")
                else:
                    lines.append(f"  `{ts}` {ev_icon}{ev.event_type.value}")

        lines.append("")

    return "\n".join(lines)


def render_run_summary(idx: int, run: V1TaskSummary) -> str:
    """One-line summary for a run in the list view."""
    icon = STATUS_ICON.get(run.status, "?")
    name = run.display_name or run.workflow_name or "?"
    run_id = run.workflow_run_external_id or "?"
    dur = _fmt_duration(run.duration)
    started = _fmt_time(run.started_at)
    meta = ""
    if run.additional_metadata:
        meta_parts = [f"{k}=`{v}`" for k, v in run.additional_metadata.items()]
        meta = f"  ({', '.join(meta_parts)})"
    return (
        f"  {idx}. {icon} **{name}** started={started} dur={dur}{meta}\n"
        f"     `{run_id}`"
    )


async def _fetch_run_list(
    count: int = 5,
    statuses: list[V1TaskStatus] | None = None,
) -> list[V1TaskSummary]:
    client = HatchetClientManager.get_client()
    since = datetime.now(timezone.utc) - timedelta(days=7)
    runs = await client.runs.aio_list(
        since=since,
        statuses=statuses,
        limit=count,
    )
    return runs.rows or []


async def list_recent_runs(
    count: int = 5,
    statuses: list[V1TaskStatus] | None = None,
) -> str:
    """List recent workflow runs as text."""
    rows = await _fetch_run_list(count, statuses)

    if not rows:
        return "No runs found in the last 7 days."

    lines = [f"Recent runs ({len(rows)}):", ""]
    for i, run in enumerate(rows, 1):
        lines.append(render_run_summary(i, run))

    lines.append("")
    lines.append("Use `--show N` to see full DAG for run N")
    return "\n".join(lines)


async def show_run(workflow_run_id: str) -> str:
    """Fetch and render a single run."""
    client = HatchetClientManager.get_client()
    details = await client.runs.aio_get(workflow_run_id)
    return render_run_detail(details)


async def show_nth_run(
    n: int,
    count: int = 5,
    statuses: list[V1TaskStatus] | None = None,
) -> str:
    """Fetch list, then drill into Nth run."""
    rows = await _fetch_run_list(count, statuses)

    if not rows:
        return "No runs found in the last 7 days."
    if n < 1 or n > len(rows):
        return f"Invalid index {n}. Have {len(rows)} runs (1-{len(rows)})."

    run = rows[n - 1]
    return await show_run(run.workflow_run_external_id)


async def main_async(args: argparse.Namespace) -> None:
    statuses = [V1TaskStatus(args.status)] if args.status else None

    if args.run_id:
        output = await show_run(args.run_id)
    elif args.show is not None:
        output = await show_nth_run(args.show, count=args.last, statuses=statuses)
    else:
        output = await list_recent_runs(count=args.last, statuses=statuses)

    print(output)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Render Hatchet workflow runs as text DAG"
    )
    parser.add_argument(
        "run_id",
        nargs="?",
        default=None,
        help="Workflow run ID to show in detail. If omitted, lists recent runs.",
    )
    parser.add_argument(
        "--show",
        type=int,
        default=None,
        metavar="N",
        help="Show full DAG for the Nth run in the list (1-indexed)",
    )
    parser.add_argument(
        "--last",
        type=int,
        default=5,
        help="Number of recent runs to list (default: 5)",
    )
    parser.add_argument(
        "--status",
        choices=["QUEUED", "RUNNING", "COMPLETED", "FAILED", "CANCELLED"],
        help="Filter by status",
    )

    args = parser.parse_args()
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()
