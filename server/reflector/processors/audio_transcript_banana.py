"""
Implementation using the GPU service from banana.

API will be a POST request to TRANSCRIPT_URL:

```json
{
    "audio_url": "https://...",
    "audio_ext": "wav",
    "timestamp": 123.456
    "language": "eng"
}
```

"""

from pathlib import Path

import httpx
from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, Word
from reflector.settings import settings
from reflector.storage import Storage
from reflector.utils.retry import retry


class AudioTranscriptBananaProcessor(AudioTranscriptProcessor):
    def __init__(self, banana_api_key: str, banana_model_key: str):
        super().__init__()
        self.transcript_url = settings.TRANSCRIPT_URL
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.storage = Storage.get_instance(
            settings.TRANSCRIPT_STORAGE_BACKEND, "TRANSCRIPT_STORAGE_"
        )
        self.headers = {
            "X-Banana-API-Key": banana_api_key,
            "X-Banana-Model-Key": banana_model_key,
        }

    async def _transcript(self, data: AudioFile):
        async with httpx.AsyncClient() as client:
            print(f"Uploading audio {data.path.name} to S3")
            url = await self._upload_file(data.path)

            print(f"Try to transcribe audio {data.path.name}")
            request_data = {
                "audio_url": url,
                "audio_ext": data.path.suffix[1:],
                "timestamp": float(round(data.timestamp, 2)),
            }
            response = await retry(client.post)(
                self.transcript_url,
                json=request_data,
                headers=self.headers,
                timeout=self.timeout,
            )

            print(f"Transcript response: {response.status_code} {response.content}")
            response.raise_for_status()
            result = response.json()
            transcript = Transcript(
                text=result["text"],
                words=[
                    Word(text=word["text"], start=word["start"], end=word["end"])
                    for word in result["words"]
                ],
            )

            # remove audio file from S3
            await self._delete_file(data.path)

        return transcript

    @retry
    async def _upload_file(self, path: Path) -> str:
        upload_result = await self.storage.put_file(path.name, open(path, "rb"))
        return upload_result.url

    @retry
    async def _delete_file(self, path: Path):
        await self.storage.delete_file(path.name)
        return True


AudioTranscriptAutoProcessor.register("banana", AudioTranscriptBananaProcessor)
