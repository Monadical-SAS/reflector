"""
Hatchet child workflow: TranscriptionWorkflow
Handles individual audio track transcription only.
"""

from datetime import timedelta

from hatchet_sdk import Context
from pydantic import BaseModel

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.constants import TIMEOUT_HEAVY
from reflector.hatchet.workflows.models import TranscribeTrackResult
from reflector.logger import logger
from reflector.utils.audio_constants import PRESIGNED_URL_EXPIRATION_SECONDS


class TranscriptionInput(BaseModel):
    """Input for individual track transcription."""

    track_index: int
    padded_key: str  # S3 key from padding step
    bucket_name: str | None  # None = use default bucket
    language: str = "en"


hatchet = HatchetClientManager.get_client()

transcription_workflow = hatchet.workflow(
    name="TranscriptionWorkflow", input_validator=TranscriptionInput
)


@transcription_workflow.task(
    execution_timeout=timedelta(seconds=TIMEOUT_HEAVY), retries=3
)
async def transcribe_track(
    input: TranscriptionInput, ctx: Context
) -> TranscribeTrackResult:
    """Transcribe audio track using GPU (Modal.com) or local Whisper."""
    ctx.log(f"transcribe_track: track {input.track_index}, language={input.language}")
    logger.info(
        "[Hatchet] transcribe_track",
        track_index=input.track_index,
        language=input.language,
    )

    try:
        from reflector.settings import settings  # noqa: PLC0415
        from reflector.storage.storage_aws import AwsStorage  # noqa: PLC0415

        storage = AwsStorage(
            aws_bucket_name=settings.TRANSCRIPT_STORAGE_AWS_BUCKET_NAME,
            aws_region=settings.TRANSCRIPT_STORAGE_AWS_REGION,
            aws_access_key_id=settings.TRANSCRIPT_STORAGE_AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.TRANSCRIPT_STORAGE_AWS_SECRET_ACCESS_KEY,
        )

        audio_url = await storage.get_file_url(
            input.padded_key,
            operation="get_object",
            expires_in=PRESIGNED_URL_EXPIRATION_SECONDS,
            bucket=input.bucket_name,
        )

        from reflector.pipelines.transcription_helpers import (  # noqa: PLC0415
            transcribe_file_with_processor,
        )

        transcript = await transcribe_file_with_processor(audio_url, input.language)

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
        logger.error(
            "[Hatchet] transcribe_track failed",
            track_index=input.track_index,
            padded_key=input.padded_key,
            language=input.language,
            error=str(e),
            exc_info=True,
        )
        raise
