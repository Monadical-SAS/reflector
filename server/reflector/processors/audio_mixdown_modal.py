"""
Modal.com backend for audio mixdown.

Uses Modal's CPU containers to offload audio mixing from Hatchet workers.
Communicates via presigned S3 URLs for both input and output.
"""

import httpx
from pydantic import BaseModel

from reflector.settings import settings


class MixdownResponse(BaseModel):
    """Response from Modal mixdown endpoint."""

    duration_ms: float
    tracks_mixed: int
    audio_uploaded: bool


class AudioMixdownModalProcessor:
    """Audio mixdown processor using Modal.com CPU backend.

    Sends track URLs (presigned GET) and output URL (presigned PUT) to Modal.
    Modal handles download, mixdown via PyAV, and upload.
    """

    def __init__(self, modal_api_key: str | None = None):
        if not settings.MIXDOWN_URL:
            raise ValueError("MIXDOWN_URL required to use AudioMixdownModalProcessor")

        self.mixdown_url = settings.MIXDOWN_URL + "/v1"
        self.timeout = settings.MIXDOWN_TIMEOUT
        self.modal_api_key = modal_api_key or settings.MIXDOWN_MODAL_API_KEY

        if not self.modal_api_key:
            raise ValueError(
                "MIXDOWN_MODAL_API_KEY required to use AudioMixdownModalProcessor"
            )

    async def mixdown(
        self,
        track_urls: list[str],
        output_url: str,
        target_sample_rate: int,
        expected_duration_sec: float | None = None,
    ) -> MixdownResponse:
        """Mix multiple audio tracks via Modal backend.

        Args:
            track_urls: List of presigned GET URLs for audio tracks (non-empty)
            output_url: Presigned PUT URL for output MP3
            target_sample_rate: Sample rate for output (Hz, must be positive)
            expected_duration_sec: Optional fallback duration if container metadata unavailable

        Returns:
            MixdownResponse with duration_ms, tracks_mixed, audio_uploaded

        Raises:
            ValueError: If track_urls is empty or target_sample_rate invalid
            httpx.HTTPStatusError: On HTTP errors (404, 403, 500, etc.)
            httpx.TimeoutException: On timeout
        """
        # Validate inputs
        if not track_urls:
            raise ValueError("track_urls cannot be empty")
        if target_sample_rate <= 0:
            raise ValueError(
                f"target_sample_rate must be positive, got {target_sample_rate}"
            )
        if expected_duration_sec is not None and expected_duration_sec < 0:
            raise ValueError(
                f"expected_duration_sec cannot be negative, got {expected_duration_sec}"
            )

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.mixdown_url}/audio/mixdown",
                headers={"Authorization": f"Bearer {self.modal_api_key}"},
                json={
                    "track_urls": track_urls,
                    "output_url": output_url,
                    "target_sample_rate": target_sample_rate,
                    "expected_duration_sec": expected_duration_sec,
                },
            )
            response.raise_for_status()
            return MixdownResponse(**response.json())
