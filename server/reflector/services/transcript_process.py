"""
Transcript processing service - shared logic for HTTP endpoints and Celery tasks.

This module provides result-based error handling that works in both contexts:
- HTTP endpoint: converts errors to HTTPException
- Celery task: converts errors to Exception
"""

from dataclasses import dataclass
from typing import Literal, Union, assert_never

import celery
from celery.result import AsyncResult
from hatchet_sdk.clients.rest.exceptions import ApiException, NotFoundException
from hatchet_sdk.clients.rest.models import V1TaskStatus

from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import Transcript, transcripts_controller
from reflector.hatchet.client import HatchetClientManager
from reflector.logger import logger
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.utils.string import NonEmptyString


@dataclass
class ProcessError:
    detail: NonEmptyString


@dataclass
class FileProcessingConfig:
    transcript_id: NonEmptyString
    mode: Literal["file"] = "file"


@dataclass
class MultitrackProcessingConfig:
    transcript_id: NonEmptyString
    bucket_name: NonEmptyString
    track_keys: list[str]
    recording_id: NonEmptyString | None = None
    room_id: NonEmptyString | None = None
    mode: Literal["multitrack"] = "multitrack"


ProcessingConfig = Union[FileProcessingConfig, MultitrackProcessingConfig]
PrepareResult = Union[ProcessingConfig, ProcessError]


@dataclass
class ValidationOk:
    # transcript currently doesnt always have recording_id
    recording_id: NonEmptyString | None
    transcript_id: NonEmptyString
    room_id: NonEmptyString | None = None


@dataclass
class ValidationLocked:
    detail: NonEmptyString


@dataclass
class ValidationNotReady:
    detail: NonEmptyString


@dataclass
class ValidationAlreadyScheduled:
    detail: NonEmptyString


ValidationError = Union[
    ValidationNotReady, ValidationLocked, ValidationAlreadyScheduled
]
ValidationResult = Union[ValidationOk, ValidationError]


@dataclass
class DispatchOk:
    status: Literal["ok"] = "ok"


@dataclass
class DispatchAlreadyRunning:
    status: Literal["already_running"] = "already_running"


DispatchResult = Union[
    DispatchOk, DispatchAlreadyRunning, ProcessError, ValidationError
]


async def validate_transcript_for_processing(
    transcript: Transcript,
) -> ValidationResult:
    if transcript.locked:
        return ValidationLocked(detail="Recording is locked")

    # Check if recording is ready for processing
    if transcript.status == "idle" and not transcript.workflow_run_id:
        return ValidationNotReady(detail="Recording is not ready for processing")

    # Check Celery tasks
    if task_is_scheduled_or_active(
        "reflector.pipelines.main_file_pipeline.task_pipeline_file_process",
        transcript_id=transcript.id,
    ) or task_is_scheduled_or_active(
        "reflector.pipelines.main_multitrack_pipeline.task_pipeline_multitrack_process",
        transcript_id=transcript.id,
    ):
        return ValidationAlreadyScheduled(detail="already running")

    # Check Hatchet workflow status if workflow_run_id exists
    if transcript.workflow_run_id:
        try:
            status = await HatchetClientManager.get_workflow_run_status(
                transcript.workflow_run_id
            )
            if status in (V1TaskStatus.RUNNING, V1TaskStatus.QUEUED):
                return ValidationAlreadyScheduled(
                    detail="Hatchet workflow already running"
                )
        except ApiException:
            # Workflow might be gone (404) or API issue - allow processing
            pass

    return ValidationOk(
        recording_id=transcript.recording_id,
        transcript_id=transcript.id,
        room_id=transcript.room_id,
    )


async def prepare_transcript_processing(validation: ValidationOk) -> PrepareResult:
    """
    Determine processing mode from transcript/recording data.
    """
    bucket_name: str | None = None
    track_keys: list[str] | None = None
    recording_id: str | None = validation.recording_id

    if validation.recording_id:
        recording = await recordings_controller.get_by_id(validation.recording_id)
        if recording:
            bucket_name = recording.bucket_name
            track_keys = recording.track_keys

            if track_keys is not None and len(track_keys) == 0:
                return ProcessError(
                    detail="No track keys found, must be either > 0 or None",
                )
            if track_keys is not None and not bucket_name:
                return ProcessError(
                    detail="Bucket name must be specified",
                )

    if track_keys:
        return MultitrackProcessingConfig(
            bucket_name=bucket_name,  # type: ignore (validated above)
            track_keys=track_keys,
            transcript_id=validation.transcript_id,
            recording_id=recording_id,
            room_id=validation.room_id,
        )

    return FileProcessingConfig(
        transcript_id=validation.transcript_id,
    )


async def dispatch_transcript_processing(
    config: ProcessingConfig, force: bool = False
) -> AsyncResult | None:
    """Dispatch transcript processing to appropriate backend (Hatchet or Celery).

    Returns AsyncResult for Celery tasks, None for Hatchet workflows.
    """
    if isinstance(config, MultitrackProcessingConfig):
        # Multitrack processing always uses Hatchet (no Celery fallback)
        # First check if we can replay (outside transaction since it's read-only)
        transcript = await transcripts_controller.get_by_id(config.transcript_id)
        if transcript and transcript.workflow_run_id and not force:
            can_replay = await HatchetClientManager.can_replay(
                transcript.workflow_run_id
            )
            if can_replay:
                await HatchetClientManager.replay_workflow(transcript.workflow_run_id)
                logger.info(
                    "Replaying Hatchet workflow",
                    workflow_id=transcript.workflow_run_id,
                )
                return None
            else:
                # Workflow can't replay (CANCELLED, COMPLETED, or 404 deleted)
                # Log and proceed to start new workflow
                try:
                    status = await HatchetClientManager.get_workflow_run_status(
                        transcript.workflow_run_id
                    )
                    logger.info(
                        "Old workflow not replayable, starting new",
                        old_workflow_id=transcript.workflow_run_id,
                        old_status=status.value,
                    )
                except NotFoundException:
                    # Workflow deleted from Hatchet but ID still in DB
                    logger.info(
                        "Old workflow not found in Hatchet, starting new",
                        old_workflow_id=transcript.workflow_run_id,
                    )

        # Force: cancel old workflow if exists
        if force and transcript and transcript.workflow_run_id:
            try:
                await HatchetClientManager.cancel_workflow(transcript.workflow_run_id)
                logger.info(
                    "Cancelled old workflow (--force)",
                    workflow_id=transcript.workflow_run_id,
                )
            except NotFoundException:
                logger.info(
                    "Old workflow already deleted (--force)",
                    workflow_id=transcript.workflow_run_id,
                )
            await transcripts_controller.update(transcript, {"workflow_run_id": None})

        # Re-fetch and check for concurrent dispatch (optimistic approach).
        # No database lock - worst case is duplicate dispatch, but Hatchet
        # workflows are idempotent so this is acceptable.
        transcript = await transcripts_controller.get_by_id(config.transcript_id)
        if transcript and transcript.workflow_run_id:
            # Another process started a workflow between validation and now
            try:
                status = await HatchetClientManager.get_workflow_run_status(
                    transcript.workflow_run_id
                )
                if status in (V1TaskStatus.RUNNING, V1TaskStatus.QUEUED):
                    logger.info(
                        "Concurrent workflow detected, skipping dispatch",
                        workflow_id=transcript.workflow_run_id,
                    )
                    return None
            except ApiException:
                # Workflow might be gone (404) or API issue - proceed with new workflow
                pass

        workflow_id = await HatchetClientManager.start_workflow(
            workflow_name="DiarizationPipeline",
            input_data={
                "recording_id": config.recording_id,
                "tracks": [{"s3_key": k} for k in config.track_keys],
                "bucket_name": config.bucket_name,
                "transcript_id": config.transcript_id,
                "room_id": config.room_id,
            },
            additional_metadata={
                "transcript_id": config.transcript_id,
                "recording_id": config.recording_id,
                "daily_recording_id": config.recording_id,
            },
        )

        if transcript:
            await transcripts_controller.update(
                transcript, {"workflow_run_id": workflow_id}
            )

        logger.info("Hatchet workflow dispatched", workflow_id=workflow_id)
        return None

    elif isinstance(config, FileProcessingConfig):
        return task_pipeline_file_process.delay(transcript_id=config.transcript_id)
    else:
        assert_never(config)


def task_is_scheduled_or_active(task_name: str, **kwargs):
    inspect = celery.current_app.control.inspect()

    scheduled = inspect.scheduled() or {}
    active = inspect.active() or {}
    all = scheduled | active
    for worker, tasks in all.items():
        for task in tasks:
            if task["name"] == task_name and task["kwargs"] == kwargs:
                return True

    return False
