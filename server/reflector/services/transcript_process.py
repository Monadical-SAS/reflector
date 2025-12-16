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

from reflector.db.recordings import recordings_controller
from reflector.db.transcripts import Transcript
from reflector.hatchet.client import HatchetClientManager
from reflector.logger import logger
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)
from reflector.settings import settings
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

    if transcript.status == "idle":
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

    # Check Hatchet workflows (if enabled)
    if settings.HATCHET_ENABLED and transcript.workflow_run_id:
        from reflector.hatchet.client import HatchetClientManager

        try:
            status = await HatchetClientManager.get_workflow_run_status(
                transcript.workflow_run_id
            )
            # If workflow is running or queued, don't allow new processing
            if "RUNNING" in status or "QUEUED" in status:
                return ValidationAlreadyScheduled(
                    detail="Hatchet workflow already running"
                )
        except Exception:
            # If we can't get status, allow processing (workflow might be gone)
            pass

    return ValidationOk(
        recording_id=transcript.recording_id, transcript_id=transcript.id
    )


async def prepare_transcript_processing(
    validation: ValidationOk, room_id: str | None = None
) -> PrepareResult:
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
            room_id=room_id,
        )

    return FileProcessingConfig(
        transcript_id=validation.transcript_id,
    )


def dispatch_transcript_processing(
    config: ProcessingConfig, force: bool = False
) -> AsyncResult | None:
    if isinstance(config, MultitrackProcessingConfig):
        # Check if room has use_hatchet=True (overrides env vars)
        room_forces_hatchet = False
        if config.room_id:
            import asyncio

            from reflector.db.rooms import rooms_controller

            async def _check_room_hatchet():
                import databases

                from reflector.db import _database_context

                db = databases.Database(settings.DATABASE_URL)
                _database_context.set(db)
                await db.connect()
                try:
                    room = await rooms_controller.get_by_id(config.room_id)
                    return room.use_hatchet if room else False
                finally:
                    await db.disconnect()
                    _database_context.set(None)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    room_forces_hatchet = pool.submit(
                        asyncio.run, _check_room_hatchet()
                    ).result()
            else:
                room_forces_hatchet = asyncio.run(_check_room_hatchet())

        # Start durable workflow if enabled (Hatchet or Conductor)
        # or if room has use_hatchet=True
        durable_started = False
        use_hatchet = settings.HATCHET_ENABLED or room_forces_hatchet

        if room_forces_hatchet:
            logger.info(
                "Room forces Hatchet workflow",
                room_id=config.room_id,
                transcript_id=config.transcript_id,
            )

        if use_hatchet:
            import asyncio

            import databases

            from reflector.db import _database_context
            from reflector.db.transcripts import transcripts_controller

            async def _handle_hatchet():
                db = databases.Database(settings.DATABASE_URL)
                _database_context.set(db)
                await db.connect()

                try:
                    transcript = await transcripts_controller.get_by_id(
                        config.transcript_id
                    )

                    if transcript and transcript.workflow_run_id and not force:
                        can_replay = await HatchetClientManager.can_replay(
                            transcript.workflow_run_id
                        )
                        if can_replay:
                            await HatchetClientManager.replay_workflow(
                                transcript.workflow_run_id
                            )
                            logger.info(
                                "Replaying Hatchet workflow",
                                workflow_id=transcript.workflow_run_id,
                            )
                            return transcript.workflow_run_id

                    # Force: cancel old workflow if exists
                    if force and transcript and transcript.workflow_run_id:
                        await HatchetClientManager.cancel_workflow(
                            transcript.workflow_run_id
                        )
                        logger.info(
                            "Cancelled old workflow (--force)",
                            workflow_id=transcript.workflow_run_id,
                        )
                        await transcripts_controller.update(
                            transcript, {"workflow_run_id": None}
                        )

                    # Re-fetch transcript to check for concurrent dispatch (TOCTOU protection)
                    transcript = await transcripts_controller.get_by_id(
                        config.transcript_id
                    )
                    if transcript and transcript.workflow_run_id:
                        # Another process started a workflow between validation and now
                        try:
                            status = await HatchetClientManager.get_workflow_run_status(
                                transcript.workflow_run_id
                            )
                            if "RUNNING" in status or "QUEUED" in status:
                                logger.info(
                                    "Concurrent workflow detected, skipping dispatch",
                                    workflow_id=transcript.workflow_run_id,
                                )
                                return transcript.workflow_run_id
                        except Exception:
                            # If we can't get status, proceed with new workflow
                            pass

                    workflow_id = await HatchetClientManager.start_workflow(
                        workflow_name="DiarizationPipeline",
                        input_data={
                            "recording_id": config.recording_id,
                            "room_name": None,
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

                    return workflow_id
                finally:
                    await db.disconnect()
                    _database_context.set(None)

            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None

            if loop and loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    workflow_id = pool.submit(asyncio.run, _handle_hatchet()).result()
            else:
                workflow_id = asyncio.run(_handle_hatchet())

            logger.info("Hatchet workflow dispatched", workflow_id=workflow_id)
            durable_started = True

        # If durable workflow started, skip Celery
        if durable_started:
            return None

        # Celery pipeline (durable workflows disabled)
        return task_pipeline_multitrack_process.delay(
            transcript_id=config.transcript_id,
            bucket_name=config.bucket_name,
            track_keys=config.track_keys,
        )
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
