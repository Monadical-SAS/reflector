"""
Modal.com backend for audio padding.

Uses Modal Python SDK to call Modal functions directly.
"""

import asyncio
import os

import modal
from pydantic import BaseModel


class PaddingResponse(BaseModel):
    """Response from Modal padding function."""

    size: int
    audio_uploaded: bool


class AudioPaddingModalProcessor:
    """Audio padding processor using Modal.com CPU backend via SDK."""

    def __init__(self):
        # Validate Modal credentials exist
        if not os.getenv("MODAL_TOKEN_ID") or not os.getenv("MODAL_TOKEN_SECRET"):
            raise ValueError(
                "Modal credentials missing. Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET environment variables."
            )

        try:
            self.padding_fn = modal.Function.from_name(
                "reflector-padding", "pad_track_direct"
            )
        except modal.exception.AuthError as e:
            raise ValueError(f"Modal authentication failed: {e}") from e
        except modal.exception.NotFoundError as e:
            raise ValueError(
                f"Modal function 'reflector-padding.pad_track_direct' not found: {e}"
            ) from e

    async def pad_track(
        self,
        track_url: str,
        output_url: str,
        start_time_seconds: float,
        track_index: int,
    ) -> PaddingResponse:
        """Pad audio track with silence via Modal backend.

        Args:
            track_url: Presigned GET URL for source audio track
            output_url: Presigned PUT URL for output WebM
            start_time_seconds: Amount of silence to prepend
            track_index: Track index for logging

        Returns:
            PaddingResponse with size and audio_uploaded
        """
        if not track_url:
            raise ValueError("track_url cannot be empty")
        if start_time_seconds <= 0:
            raise ValueError(
                f"start_time_seconds must be positive, got {start_time_seconds}"
            )

        fc = self.padding_fn.spawn(
            track_url=track_url,
            output_url=output_url,
            start_time_seconds=start_time_seconds,
            track_index=track_index,
        )

        try:
            result = await fc.get.aio()
            return PaddingResponse(**result)
        except asyncio.CancelledError:
            # Hatchet task cancelled - terminate Modal container immediately
            fc.cancel(terminate_containers=True)
            raise
        except modal.exception.FunctionTimeoutError as e:
            # Modal function exceeded timeout (configured in deployment)
            fc.cancel(terminate_containers=True)
            raise Exception(f"Modal padding timeout: {e}") from e
        except modal.exception.ExecutionError as e:
            # Modal function crashed (PyAV error, S3 upload failed, etc.)
            fc.cancel(terminate_containers=True)
            raise Exception(f"Modal padding execution failed: {e}") from e
        except Exception:
            # Unexpected error - always cancel Modal task to prevent orphans
            fc.cancel(terminate_containers=True)
            raise
