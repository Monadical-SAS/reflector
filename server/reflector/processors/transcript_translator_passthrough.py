from reflector.processors.transcript_translator import TranscriptTranslatorProcessor
from reflector.processors.transcript_translator_auto import (
    TranscriptTranslatorAutoProcessor,
)


class TranscriptTranslatorPassthroughProcessor(TranscriptTranslatorProcessor):
    async def _translate(self, text: str) -> None:
        return None


TranscriptTranslatorAutoProcessor.register(
    "passthrough", TranscriptTranslatorPassthroughProcessor
)
