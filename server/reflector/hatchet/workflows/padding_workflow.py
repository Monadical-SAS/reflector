"""
Hatchet child workflow: PaddingWorkflow
Handles individual audio track padding only.
"""

import tempfile
from datetime import timedelta
from pathlib import Path

import av
from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.constants import TIMEOUT_AUDIO
from reflector.hatchet.workflows.models import PadTrackResult
from reflector.logger import logger
from reflector.utils.audio_constants import PRESIGNED_URL_EXPIRATION_SECONDS
from reflector.utils.audio_padding import (
    apply_audio_padding_to_file,
    extract_stream_start_time_from_container,
)


class PaddingInput(BaseModel):
    """Input for individual track padding."""

    track_index: int
    s3_key: str
    bucket_name: str
    transcript_id: str


hatchet = HatchetClientManager.get_client()

padding_workflow = hatchet.workflow(
    name="PaddingWorkflow", input_validator=PaddingInput
)


@padding_workflow.task(execution_timeout=timedelta(seconds=TIMEOUT_AUDIO), retries=3)
async def pad_track(input: PaddingInput, ctx: Context) -> PadTrackResult:
    """Pad audio track with silence based on WebM container start_time."""
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

        # Extract start_time to determine if padding needed
        with av.open(source_url) as in_container:
            if in_container.duration:
                try:
                    duration = timedelta(seconds=in_container.duration // 1_000_000)
                    ctx.log(
                        f"pad_track: track {input.track_index}, duration={duration}"
                    )
                except (ValueError, TypeError, OverflowError) as e:
                    ctx.log(
                        f"pad_track: track {input.track_index}, duration error: {str(e)}"
                    )

            start_time_seconds = extract_stream_start_time_from_container(
                in_container, input.track_index, logger=logger
            )

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

        storage_path = f"file_pipeline_hatchet/{input.transcript_id}/tracks/padded_{input.track_index}.webm"

        # Conditional: Modal or local backend
        if settings.PADDING_BACKEND == "modal":
            ctx.log("pad_track: using Modal backend")

            # Presign PUT URL for output (Modal will upload directly)
            output_url = await storage.get_file_url(
                storage_path,
                operation="put_object",
                expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
            )

            # Import Modal-specific dependencies inside conditional (only needed for Modal backend)
            import httpx  # noqa: PLC0415

            from reflector.processors.audio_padding_modal import (  # noqa: PLC0415
                AudioPaddingModalProcessor,
            )

            try:
                processor = AudioPaddingModalProcessor()
                result = await processor.pad_track(
                    track_url=source_url,
                    output_url=output_url,
                    start_time_seconds=start_time_seconds,
                    track_index=input.track_index,
                )
                file_size = result.size

                ctx.log(f"pad_track: Modal returned size={file_size}")
            except httpx.HTTPStatusError as e:
                error_detail = (
                    e.response.text if hasattr(e.response, "text") else str(e)
                )
                logger.error(
                    "[Hatchet] Modal padding HTTP error",
                    transcript_id=input.transcript_id,
                    track_index=input.track_index,
                    status_code=e.response.status_code
                    if hasattr(e, "response")
                    else None,
                    error=error_detail,
                    exc_info=True,
                )
                raise Exception(
                    f"Modal padding failed: HTTP {e.response.status_code}"
                ) from e
            except httpx.TimeoutException as e:
                logger.error(
                    "[Hatchet] Modal padding timeout",
                    transcript_id=input.transcript_id,
                    track_index=input.track_index,
                    error=str(e),
                    exc_info=True,
                )
                raise Exception("Modal padding timeout") from e

        else:
            # Local PyAV padding
            ctx.log("pad_track: using local PyAV backend")

            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as temp_file:
                temp_path = temp_file.name

            try:
                with av.open(source_url) as in_container:
                    apply_audio_padding_to_file(
                        in_container,
                        temp_path,
                        start_time_seconds,
                        input.track_index,
                        logger=logger,
                    )

                file_size = Path(temp_path).stat().st_size

                with open(temp_path, "rb") as padded_file:
                    await storage.put_file(storage_path, padded_file)

                logger.info(
                    f"Uploaded padded track to S3",
                    key=storage_path,
                    size=file_size,
                )
            finally:
                Path(temp_path).unlink(missing_ok=True)

        logger.info(
            "[Hatchet] pad_track complete",
            track_index=input.track_index,
            padded_key=storage_path,
        )

        return PadTrackResult(
            padded_key=storage_path,
            bucket_name=None,  # None = use default transcript storage bucket
            size=file_size,
            track_index=input.track_index,
        )

    except Exception as e:
        logger.error(
            "[Hatchet] pad_track failed",
            transcript_id=input.transcript_id,
            track_index=input.track_index,
            error=str(e),
            exc_info=True,
        )
        raise
