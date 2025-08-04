from reflector.processors.base import Processor
from reflector.processors.types import Transcript


class TranscriptTranslatorProcessor(Processor):
    """
    Translate the transcript into the target language
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = Transcript

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.transcript = None

    async def _push(self, data: Transcript):
        self.transcript = data
        await self.flush()

    async def _translate(self, text: str) -> str | None:
        raise NotImplementedError

    async def _flush(self):
        if not self.transcript:
            return

        source_language = self.get_pref("audio:source_language", "en")
        target_language = self.get_pref("audio:target_language", "en")
        if source_language == target_language:
            self.transcript.translation = None
        else:
            self.transcript.translation = await self._translate(self.transcript.text)

        await self.emit(self.transcript)
