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

from openai import AsyncOpenAI

from reflector.processors.audio_transcript import AudioTranscriptProcessor
from reflector.processors.audio_transcript_auto import AudioTranscriptAutoProcessor
from reflector.processors.types import AudioFile, Transcript, Word
from reflector.settings import settings


class AudioTranscriptModalProcessor(AudioTranscriptProcessor):
    def __init__(self, modal_api_key: str | None = None, **kwargs):
        super().__init__()
        if not settings.TRANSCRIPT_URL:
            raise Exception(
                "TRANSCRIPT_URL required to use AudioTranscriptModalProcessor"
            )
        self.transcript_url = settings.TRANSCRIPT_URL + "/v1"
        self.timeout = settings.TRANSCRIPT_TIMEOUT
        self.modal_api_key = modal_api_key

    async def _transcript(self, data: AudioFile):
        api_key = f"Bearer {self.modal_api_key}" if self.modal_api_key else None
        async with AsyncOpenAI(
            base_url=self.transcript_url,
            api_key=api_key,
            timeout=self.timeout,
        ) as client:
            self.logger.debug(f"Try to transcribe audio {data.name}")

            audio_file = open(data.path, "rb")
            transcription = await client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-1",
                response_format="verbose_json",
                language=self.get_pref("audio:source_language", "en"),
                timestamp_granularities=["word"],
            )
            self.logger.debug(f"Transcription: {transcription}")
            transcript = Transcript(
                words=[
                    Word(
                        text=word.word,
                        start=word.start,
                        end=word.end,
                    )
                    for word in transcription.words
                ],
            )
            transcript.add_offset(data.timestamp)

        return transcript


AudioTranscriptAutoProcessor.register("modal", AudioTranscriptModalProcessor)
