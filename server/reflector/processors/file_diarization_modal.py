"""
File diarization implementation using the GPU service from modal.com

API will be a POST request to DIARIZATION_URL:

```
POST /diarize?audio_file_url=...&timestamp=0
Authorization: Bearer <modal_api_key>
```
"""

import httpx

from reflector.processors.file_diarization import (
    FileDiarizationInput,
    FileDiarizationOutput,
    FileDiarizationProcessor,
)
from reflector.processors.file_diarization_auto import FileDiarizationAutoProcessor
from reflector.settings import settings


class FileDiarizationModalProcessor(FileDiarizationProcessor):
    def __init__(self, modal_api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if not settings.DIARIZATION_URL:
            raise Exception(
                "DIARIZATION_URL required to use FileDiarizationModalProcessor"
            )
        self.diarization_url = settings.DIARIZATION_URL + "/diarize"
        self.file_timeout = settings.DIARIZATION_FILE_TIMEOUT
        self.modal_api_key = modal_api_key

    async def _diarize(self, data: FileDiarizationInput):
        """Get speaker diarization for file"""
        self.logger.info(f"Starting diarization from {data.audio_url}")

        headers = {}
        if self.modal_api_key:
            headers["Authorization"] = f"Bearer {self.modal_api_key}"

        async with httpx.AsyncClient(timeout=self.file_timeout) as client:
            response = await client.post(
                self.diarization_url,
                headers=headers,
                params={
                    "audio_file_url": data.audio_url,
                    "timestamp": 0,
                },
            )
            response.raise_for_status()
            diarization_data = response.json()["diarization"]

        return FileDiarizationOutput(diarization=diarization_data)


FileDiarizationAutoProcessor.register("modal", FileDiarizationModalProcessor)
