"""
File transcription implementation using the GPU service from modal.com

API will be a POST request to TRANSCRIPT_URL:

```json
{
    "audio_file_url": "https://...",
    "language": "en",
    "model": "parakeet-tdt-0.6b-v2",
    "batch": true
}
```
"""

import httpx

from reflector.processors.file_transcript import (
    FileTranscriptInput,
    FileTranscriptProcessor,
)
from reflector.processors.file_transcript_auto import FileTranscriptAutoProcessor
from reflector.processors.types import Transcript, Word
from reflector.settings import settings


class FileTranscriptModalProcessor(FileTranscriptProcessor):
    def __init__(self, modal_api_key: str | None = None, **kwargs):
        super().__init__(**kwargs)
        if not settings.TRANSCRIPT_URL:
            raise Exception(
                "TRANSCRIPT_URL required to use FileTranscriptModalProcessor"
            )
        self.transcript_url = settings.TRANSCRIPT_URL
        self.file_timeout = settings.TRANSCRIPT_FILE_TIMEOUT
        self.modal_api_key = modal_api_key

    async def _transcript(self, data: FileTranscriptInput):
        """Send full file to Modal for transcription"""
        url = f"{self.transcript_url}/v1/audio/transcriptions-from-url"

        self.logger.info(f"Starting file transcription from {data.audio_url}")

        headers = {}
        if self.modal_api_key:
            headers["Authorization"] = f"Bearer {self.modal_api_key}"

        async with httpx.AsyncClient(timeout=self.file_timeout) as client:
            response = await client.post(
                url,
                headers=headers,
                json={
                    "audio_file_url": data.audio_url,
                    "language": data.language,
                    "batch": True,
                },
                follow_redirects=True,
            )

            if response.status_code != 200:
                error_body = response.text
                self.logger.error(
                    "Modal API error",
                    audio_url=data.audio_url,
                    status_code=response.status_code,
                    error_body=error_body,
                )

            response.raise_for_status()
            result = response.json()

        words = [
            Word(
                text=word_info["word"],
                start=word_info["start"],
                end=word_info["end"],
            )
            for word_info in result.get("words", [])
        ]

        # words come not in order
        words.sort(key=lambda w: w.start)

        return Transcript(words=words)


# Register with the auto processor
FileTranscriptAutoProcessor.register("modal", FileTranscriptModalProcessor)
