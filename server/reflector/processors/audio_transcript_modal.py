"""
Implementation using the GPU service from modal.com

API will be a POST request to TRANSCRIPT_URL:

```form
"timestamp": 123.456
"language": "en"
"file": <audio file>
```

"""

from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, Word
from reflector.settings import settings
from reflector.utils.retry import retry
from time import monotonic
import httpx


class AudioTranscriptModalProcessor(AudioTranscriptProcessor):
    def __init__(self, modal_api_key: str):
        super().__init__()
        self.transcript_url = settings.TRANSCRIPT_URL + "/transcribe"
        self.warmup_url = settings.TRANSCRIPT_URL + "/warmup"
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {modal_api_key}",
        }

    async def _warmup(self):
        try:
            async with httpx.AsyncClient() as client:
                start = monotonic()
                self.logger.debug("Transcribe modal: warming up...")
                response = await client.post(
                    self.warmup_url,
                    headers=self.headers,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                duration = monotonic() - start
                self.logger.debug(f"Transcribe modal: warmup took {duration:.2f}s")
        except Exception:
            self.logger.exception("Transcribe modal: warmup failed")

    async def _transcript(self, data: AudioFile):
        async with httpx.AsyncClient() as client:
            self.logger.debug(f"Try to transcribe audio {data.path.name}")
            files = {
                "file": (data.path.name, data.path.open("rb")),
            }
            response = await retry(client.post)(
                self.transcript_url,
                files=files,
                timeout=self.timeout,
                headers=self.headers,
            )

            self.logger.debug(
                f"Transcript response: {response.status_code} {response.content}"
            )
            response.raise_for_status()
            result = response.json()
            transcript = Transcript(
                text=result["text"],
                words=[
                    Word(
                        text=word["text"],
                        start=word["start"],
                        end=word["end"],
                    )
                    for word in result["words"]
                ],
            )
            transcript.add_offset(data.timestamp)

        return transcript


AudioTranscriptAutoProcessor.register("modal", AudioTranscriptModalProcessor)
