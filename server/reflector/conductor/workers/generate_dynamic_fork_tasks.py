"""Conductor worker: generate_dynamic_fork_tasks - Helper for FORK_JOIN_DYNAMIC."""

from conductor.client.http.models import Task, TaskResult
from conductor.client.http.models.task_result_status import TaskResultStatus
from conductor.client.worker.worker_task import worker_task
from reflector.logger import logger


@worker_task(task_definition_name="generate_dynamic_fork_tasks")
def generate_dynamic_fork_tasks(task: Task) -> TaskResult:
    """Generate dynamic fork task structure for variable track counts.

    This helper task generates the task definitions and inputs needed for
    FORK_JOIN_DYNAMIC to process N tracks in parallel.

    Input:
        tracks: list[dict] - List of track info with s3_key
        task_type: str - Either "pad_track" or "transcribe_track"
        transcript_id: str - Transcript ID
        bucket_name: str - S3 bucket name (for pad_track)
        padded_urls: list[dict] - Padded track outputs (for transcribe_track)

    Output:
        tasks: list[dict] - Task definitions for dynamic fork
        inputs: dict - Input parameters keyed by task reference name
    """
    tracks = task.input_data.get("tracks", [])
    task_type = task.input_data.get("task_type")
    transcript_id = task.input_data.get("transcript_id")
    bucket_name = task.input_data.get("bucket_name")
    padded_urls = task.input_data.get("padded_urls", {})

    logger.info(
        "[Worker] generate_dynamic_fork_tasks",
        task_type=task_type,
        track_count=len(tracks),
    )

    task_result = TaskResult(
        task_id=task.task_id,
        workflow_instance_id=task.workflow_instance_id,
        worker_id=task.worker_id,
    )

    if not tracks or not task_type:
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = "Missing tracks or task_type"
        return task_result

    try:
        tasks = []
        inputs = {}

        for idx, track in enumerate(tracks):
            ref_name = f"{task_type}_{idx}"

            # Task definition
            tasks.append(
                {
                    "name": task_type,
                    "taskReferenceName": ref_name,
                    "type": "SIMPLE",
                }
            )

            # Task input based on type
            if task_type == "pad_track":
                inputs[ref_name] = {
                    "track_index": idx,
                    "s3_key": track.get("s3_key"),
                    "bucket_name": bucket_name,
                    "transcript_id": transcript_id,
                }
            elif task_type == "transcribe_track":
                # Get padded URL from previous fork join output
                padded_url = None
                if isinstance(padded_urls, dict):
                    # Try to get from join output structure
                    pad_ref = f"pad_track_{idx}"
                    if pad_ref in padded_urls:
                        padded_url = padded_urls[pad_ref].get("padded_url")
                    elif "padded_url" in padded_urls:
                        # Single track case
                        padded_url = padded_urls.get("padded_url")

                inputs[ref_name] = {
                    "track_index": idx,
                    "audio_url": padded_url,
                    "language": "en",
                    "transcript_id": transcript_id,
                }

        task_result.status = TaskResultStatus.COMPLETED
        task_result.output_data = {
            "tasks": tasks,
            "inputs": inputs,
        }

        logger.info(
            "[Worker] generate_dynamic_fork_tasks complete",
            task_type=task_type,
            task_count=len(tasks),
        )

    except Exception as e:
        logger.error("[Worker] generate_dynamic_fork_tasks failed", error=str(e))
        task_result.status = TaskResultStatus.FAILED
        task_result.reason_for_incompletion = str(e)

    return task_result
