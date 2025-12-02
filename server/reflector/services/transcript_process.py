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
from reflector.pipelines.main_file_pipeline import task_pipeline_file_process
from reflector.pipelines.main_multitrack_pipeline import (
    task_pipeline_multitrack_process,
)
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

    if task_is_scheduled_or_active(
        "reflector.pipelines.main_file_pipeline.task_pipeline_file_process",
        transcript_id=transcript.id,
    ) or task_is_scheduled_or_active(
        "reflector.pipelines.main_multitrack_pipeline.task_pipeline_multitrack_process",
        transcript_id=transcript.id,
    ):
        return ValidationAlreadyScheduled(detail="already running")

    return ValidationOk(
        recording_id=transcript.recording_id, transcript_id=transcript.id
    )


async def prepare_transcript_processing(validation: ValidationOk) -> PrepareResult:
    """
    Determine processing mode from transcript/recording data.
    """
    bucket_name: str | None = None
    track_keys: list[str] | None = None

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
        )

    return FileProcessingConfig(
        transcript_id=validation.transcript_id,
    )


def dispatch_transcript_processing(config: ProcessingConfig) -> AsyncResult:
    if isinstance(config, MultitrackProcessingConfig):
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

    scheduled = inspect.scheduled() or []
    active = inspect.active() or []
    all = scheduled | active
    for worker, tasks in all.items():
        for task in tasks:
            if task["name"] == task_name and task["kwargs"] == kwargs:
                return True

    return False
