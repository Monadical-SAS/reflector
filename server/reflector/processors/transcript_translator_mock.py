from reflector.processors.transcript_translator import TranscriptTranslatorProcessor
from reflector.processors.transcript_translator_auto import (
    TranscriptTranslatorAutoProcessor,
)


class TranscriptTranslatorMockProcessor(TranscriptTranslatorProcessor):
    """
    Translate the transcript into the target language using Modal.com
    """

    async def _translate(self, text: str) -> None:
        return None


TranscriptTranslatorAutoProcessor.register("mock", TranscriptTranslatorMockProcessor)
