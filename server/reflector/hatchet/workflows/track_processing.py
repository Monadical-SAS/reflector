"""
Hatchet child workflow: TrackProcessing

Handles individual audio track processing: padding and transcription.
Spawned dynamically by the main diarization pipeline for each track.

Architecture note: This is a separate workflow (not inline tasks in DiarizationPipeline)
because Hatchet workflow DAGs are defined statically, but the number of tracks varies
at runtime. Child workflow spawning via `aio_run()` + `asyncio.gather()` is the
standard pattern for dynamic fan-out. See `process_tracks` in diarization_pipeline.py.

Note: This file uses deferred imports (inside tasks) intentionally.
Hatchet workers run in forked processes; fresh imports per task ensure
storage/DB connections are not shared across forks.
"""

import tempfile
from datetime import timedelta
from pathlib import Path

import av
from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.constants import TIMEOUT_AUDIO, TIMEOUT_HEAVY
from reflector.hatchet.workflows.models import PadTrackResult, TranscribeTrackResult
from reflector.logger import logger
from reflector.utils.audio_constants import PRESIGNED_URL_EXPIRATION_SECONDS
from reflector.utils.audio_padding import (
    apply_audio_padding_to_file,
    extract_stream_start_time_from_container,
)


class TrackInput(BaseModel):
    """Input for individual track processing."""

    track_index: int
    s3_key: str
    bucket_name: str
    transcript_id: str
    language: str = "en"


hatchet = HatchetClientManager.get_client()

track_workflow = hatchet.workflow(name="TrackProcessing", input_validator=TrackInput)


@track_workflow.task(execution_timeout=timedelta(seconds=TIMEOUT_AUDIO), retries=3)
async def pad_track(input: TrackInput, ctx: Context) -> PadTrackResult:
    """Pad single audio track with silence for alignment.

    Extracts stream.start_time from WebM container metadata and applies
    silence padding using PyAV filter graph (adelay).
    """
    ctx.log(f"pad_track: track {input.track_index}, s3_key={input.s3_key}")
    logger.info(
        "[Hatchet] pad_track",
        track_index=input.track_index,
        s3_key=input.s3_key,
        transcript_id=input.transcript_id,
    )

    try:
        # Create fresh storage instance to avoid aioboto3 fork issues
        from reflector.settings import settings  # noqa: PLC0415
        from reflector.storage.storage_aws import AwsStorage  # noqa: PLC0415

        storage = AwsStorage(
            aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
            aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
            aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        source_url = await storage.get_file_url(
            input.s3_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
            bucket=input.bucket_name,
        )

        with av.open(source_url) as in_container:
            start_time_seconds = extract_stream_start_time_from_container(
                in_container, input.track_index, logger=logger
            )

            # If no padding needed, return original S3 key
            if start_time_seconds <= 0:
                logger.info(
                    f"Track {input.track_index} requires no padding",
                    track_index=input.track_index,
                )
                return PadTrackResult(
                    padded_key=input.s3_key,
                    bucket_name=input.bucket_name,
                    size=0,
                    track_index=input.track_index,
                )

            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                apply_audio_padding_to_file(
                    in_container,
                    temp_path,
                    start_time_seconds,
                    input.track_index,
                    logger=logger,
                )

                file_size = Path(temp_path).stat().st_size
                storage_path = f"file_pipeline_hatchet/{input.transcript_id}/tracks/padded_{input.track_index}.webm"

                logger.info(
                    f"About to upload padded track",
                    key=storage_path,
                    size=file_size,
                )

                with open(temp_path, "rb") as padded_file:
                    await storage.put_file(storage_path, padded_file)

                logger.info(
                    f"Uploaded padded track to S3",
                    key=storage_path,
                    size=file_size,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        ctx.log(f"pad_track complete: track {input.track_index} -> {storage_path}")
        logger.info(
            "[Hatchet] pad_track complete",
            track_index=input.track_index,
            padded_key=storage_path,
        )

        # Return S3 key (not presigned URL) - consumer tasks presign on demand
        # This avoids stale URLs when workflow is replayed
        return PadTrackResult(
            padded_key=storage_path,
            bucket_name=None,  # None = use default transcript storage bucket
            size=file_size,
            track_index=input.track_index,
        )

    except Exception as e:
        logger.error("[Hatchet] pad_track failed", error=str(e), exc_info=True)
        raise


@track_workflow.task(
    parents=[pad_track], execution_timeout=timedelta(seconds=TIMEOUT_HEAVY), retries=3
)
async def transcribe_track(input: TrackInput, ctx: Context) -> TranscribeTrackResult:
    """Transcribe audio track using GPU (Modal.com) or local Whisper."""
    ctx.log(f"transcribe_track: track {input.track_index}, language={input.language}")
    logger.info(
        "[Hatchet] transcribe_track",
        track_index=input.track_index,
        language=input.language,
    )

    try:
        pad_result = ctx.task_output(pad_track)
        padded_key = pad_result.padded_key
        bucket_name = pad_result.bucket_name

        if not padded_key:
            raise ValueError("Missing padded_key from pad_track")

        # Presign URL on demand (avoids stale URLs on workflow replay)
        from reflector.settings import settings  # noqa: PLC0415
        from reflector.storage.storage_aws import AwsStorage  # noqa: PLC0415

        storage = AwsStorage(
            aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
            aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
            aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        audio_url = await storage.get_file_url(
            padded_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
            bucket=bucket_name,
        )

        from reflector.pipelines.transcription_helpers import (  # noqa: PLC0415
            transcribe_file_with_processor,
        )

        transcript = await transcribe_file_with_processor(audio_url, input.language)

        # Tag all words with speaker index
        for word in transcript.words:
            word.speaker = input.track_index

        ctx.log(
            f"transcribe_track complete: track {input.track_index}, {len(transcript.words)} words"
        )
        logger.info(
            "[Hatchet] transcribe_track complete",
            track_index=input.track_index,
            word_count=len(transcript.words),
        )

        return TranscribeTrackResult(
            words=transcript.words,
            track_index=input.track_index,
        )

    except Exception as e:
        logger.error("[Hatchet] transcribe_track failed", error=str(e), exc_info=True)
        raise
