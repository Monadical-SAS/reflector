"""
Implementation using the GPU service from modal.com

API will be a POST request to TRANSCRIPT_URL:

```form
"timestamp": 123.456
"source_language": "en"
"target_language": "en"
"file": <audio file>
```

"""

from time import monotonic

import httpx

from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, TranslationLanguages, Word
from reflector.settings import settings
from reflector.utils.retry import retry


class AudioTranscriptModalProcessor(AudioTranscriptProcessor):
    def __init__(self, modal_api_key: str):
        super().__init__()
        self.transcript_url = settings.TRANSCRIPT_URL + "/transcribe"
        self.warmup_url = settings.TRANSCRIPT_URL + "/warmup"
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.headers = {
            "Authorization": f"Bearer {modal_api_key}",
            # "Content-Type": "multipart/form-data"
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
            self.logger.debug(f"Try to transcribe audio {data.name}")
            files = {
                "file": (data.name, data.fd),
            }

            # TODO: Get the source / target language from the UI preferences dynamically
            # Update code here once this is possible.
            # i.e) extract from context/session objects
            source_language = "en"
            target_language = "en"
            languages = TranslationLanguages()

            # Only way to set the target should be the UI element like dropdown.
            # Hence, this assert should never fail.
            assert languages.is_supported(target_language)
            json_payload = {
                "source_language": source_language,
                "target_language": target_language,
            }

            response = await retry(client.post)(
                self.transcript_url,
                files=files,
                timeout=self.timeout,
                headers=self.headers,
                json=json_payload,
            )

            self.logger.debug(
                f"Transcript response: {response.status_code} {response.content}"
            )
            response.raise_for_status()
            result = response.json()

            # Sanity check for translation status in the result
            if target_language in result["text"]:
                text = result["text"][target_language]
            else:
                text = result["text"]["en"]
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
