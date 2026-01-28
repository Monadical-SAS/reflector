"""
Modal.com backend for audio padding.
"""

import asyncio
import os

import modal
from pydantic import BaseModel

from reflector.logger import logger


class PaddingResponse(BaseModel):
    size: int


class AudioPaddingModalProcessor:
    """Audio padding processor using Modal.com CPU backend via SDK."""

    def __init__(self):
        if not os.getenv("MODAL_TOKEN_ID") or not os.getenv("MODAL_TOKEN_SECRET"):
            raise ValueError(
                "Modal credentials missing. Set MODAL_TOKEN_ID and MODAL_TOKEN_SECRET environment variables."
            )

        try:
            self.padding_fn = modal.Function.from_name("reflector-padding", "pad_track")
        except modal.exception.AuthError as e:
            raise ValueError(f"Modal authentication failed: {e}") from e
        except modal.exception.NotFoundError as e:
            raise ValueError(
                f"Modal function 'reflector-padding.pad_track' not found: {e}"
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
        """
        if not track_url:
            raise ValueError("track_url cannot be empty")
        if start_time_seconds <= 0:
            raise ValueError(
                f"start_time_seconds must be positive, got {start_time_seconds}"
            )

        log = logger.bind(track_index=track_index, padding_seconds=start_time_seconds)
        log.info("Spawning Modal padding task")

        fc = self.padding_fn.spawn(
            track_url=track_url,
            output_url=output_url,
            start_time_seconds=start_time_seconds,
            track_index=track_index,
        )

        try:
            result = await fc.get.aio()
            log.info("Modal padding complete", size=result["size"])
            return PaddingResponse(**result)
        except asyncio.CancelledError:
            log.warning("Modal padding cancelled by Hatchet")
            fc.cancel(terminate_containers=True)
            raise
        except modal.exception.FunctionTimeoutError as e:
            log.error("Modal padding timeout", error=str(e), exc_info=True)
            fc.cancel(terminate_containers=True)
            raise Exception(f"Modal padding timeout: {e}") from e
        except modal.exception.ExecutionError as e:
            log.error("Modal padding execution failed", error=str(e), exc_info=True)
            fc.cancel(terminate_containers=True)
            raise Exception(f"Modal padding execution failed: {e}") from e
        except Exception as e:
            log.error("Modal padding unexpected error", error=str(e), exc_info=True)
            fc.cancel(terminate_containers=True)
            raise
