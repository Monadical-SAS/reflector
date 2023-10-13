"""
Implementation using the GPU service from modal.com

API will be a POST request to TRANSCRIPT_URL:

```form
"timestamp": 123.456
"source_language": "eng"
"target_language": "eng"
"file": <audio file>
```

"""

import httpx
from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, Word
from reflector.settings import settings
from reflector.utils.retry import retry


class AudioTranscriptModalProcessor(AudioTranscriptProcessor):
    def __init__(self, modal_api_key: str):
        super().__init__()
        self.transcript_url = settings.TRANSCRIPT_URL + "/transcribe"
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.headers = {"Authorization": f"Bearer {modal_api_key}"}

    async def _transcript(self, data: AudioFile):
        async with httpx.AsyncClient() as client:
            self.logger.debug(f"Try to transcribe audio {data.name}")
            files = {
                "file": (data.name, data.fd),
            }
            source_language = self.get_pref("audio:source_language", "eng")
            json_payload = {"source_language": source_language}
            response = await retry(client.post)(
                self.transcript_url,
                files=files,
                timeout=self.timeout,
                headers=self.headers,
                params=json_payload,
            )

            self.logger.debug(
                f"Transcript response: {response.status_code} {response.content}"
            )
            response.raise_for_status()
            result = response.json()
            text = result["text"][source_language]
            text = self.filter_profanity(text)
            transcript = Transcript(
                text=text,
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
