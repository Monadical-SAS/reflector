"""
Modal.com backend for audio padding.

Uses Modal's CPU containers to offload audio padding from Hatchet workers.
Communicates via presigned S3 URLs for both input and output.
"""

import httpx
from pydantic import BaseModel

from reflector.settings import settings


class PaddingResponse(BaseModel):
    """Response from Modal padding endpoint."""

    size: int
    audio_uploaded: bool


class AudioPaddingModalProcessor:
    """Audio padding processor using Modal.com CPU backend.

    Sends track URL (presigned GET) and output URL (presigned PUT) to Modal.
    Modal handles download, padding via PyAV, and upload.
    """

    def __init__(self, modal_api_key: str | None = None):
        if not settings.PADDING_URL:
            raise ValueError("PADDING_URL required to use AudioPaddingModalProcessor")

        self.padding_url = settings.PADDING_URL + "/v1"
        self.timeout = settings.PADDING_TIMEOUT
        self.modal_api_key = modal_api_key or settings.PADDING_MODAL_API_KEY

        if not self.modal_api_key:
            raise ValueError(
                "PADDING_MODAL_API_KEY required to use AudioPaddingModalProcessor"
            )

    async def pad_track(
        self,
        track_url: str,
        output_url: str,
        start_time_seconds: float,
        track_index: int,
    ) -> PaddingResponse:
        """Pad audio track with silence via Modal backend.

        Args:
            track_url: Presigned GET URL for source audio track (non-empty)
            output_url: Presigned PUT URL for output WebM
            start_time_seconds: Amount of silence to prepend (must be positive)
            track_index: Track index for logging/debugging

        Returns:
            PaddingResponse with size and audio_uploaded

        Raises:
            ValueError: If track_url is empty or start_time_seconds invalid
            httpx.HTTPStatusError: On HTTP errors (404, 403, 500, etc.)
            httpx.TimeoutException: On timeout
        """
        # Validate inputs
        if not track_url:
            raise ValueError("track_url cannot be empty")
        if start_time_seconds <= 0:
            raise ValueError(
                f"start_time_seconds must be positive, got {start_time_seconds}"
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.padding_url}/audio/padding",
                headers={"Authorization": f"Bearer {self.modal_api_key}"},
                json={
                    "track_url": track_url,
                    "output_url": output_url,
                    "start_time_seconds": start_time_seconds,
                    "track_index": track_index,
                },
            )
            response.raise_for_status()
            return PaddingResponse(**response.json())
