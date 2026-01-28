"""
Modal.com backend for audio padding.
"""

import asyncio
import os

import httpx
from pydantic import BaseModel

from reflector.logger import logger


class PaddingResponse(BaseModel):
    size: int
    cancelled: bool = False


class AudioPaddingModalProcessor:
    """Audio padding processor using Modal.com CPU backend via HTTP."""

    def __init__(
        self, padding_url: str | None = None, modal_api_key: str | None = None
    ):
        self.padding_url = padding_url or os.getenv("PADDING_URL")
        if not self.padding_url:
            raise ValueError(
                "PADDING_URL required to use AudioPaddingModalProcessor. "
                "Set PADDING_URL environment variable or pass padding_url parameter."
            )

        self.modal_api_key = modal_api_key or os.getenv("MODAL_API_KEY")

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
        log.info("Sending Modal padding HTTP request")

        url = f"{self.padding_url}/pad"

        headers = {}
        if self.modal_api_key:
            headers["Authorization"] = f"Bearer {self.modal_api_key}"

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    headers=headers,
                    json={
                        "track_url": track_url,
                        "output_url": output_url,
                        "start_time_seconds": start_time_seconds,
                        "track_index": track_index,
                    },
                    follow_redirects=True,
                )

                if response.status_code != 200:
                    error_body = response.text
                    log.error(
                        "Modal padding API error",
                        status_code=response.status_code,
                        error_body=error_body,
                    )

                response.raise_for_status()
                result = response.json()

            # Check if work was cancelled
            if result.get("cancelled"):
                log.warning("Modal padding was cancelled by disconnect detection")
                raise asyncio.CancelledError(
                    "Padding cancelled due to client disconnect"
                )

            log.info("Modal padding complete", size=result["size"])
            return PaddingResponse(**result)
        except asyncio.CancelledError:
            log.warning(
                "Modal padding cancelled (Hatchet timeout, disconnect detected on Modal side)"
            )
            raise
        except httpx.TimeoutException as e:
            log.error("Modal padding timeout", error=str(e), exc_info=True)
            raise Exception(f"Modal padding timeout: {e}") from e
        except httpx.HTTPStatusError as e:
            log.error("Modal padding HTTP error", error=str(e), exc_info=True)
            raise Exception(f"Modal padding HTTP error: {e}") from e
        except Exception as e:
            log.error("Modal padding unexpected error", error=str(e), exc_info=True)
            raise
