"""
Processor to assemble transcript with diarization results
"""

from reflector.processors.audio_diarization import AudioDiarizationProcessor
from reflector.processors.base import Processor
from reflector.processors.types import DiarizationSegment, Transcript


class TranscriptDiarizationAssemblerInput:
    """Input containing transcript and diarization data"""

    def __init__(self, transcript: Transcript, diarization: list[DiarizationSegment]):
        self.transcript = transcript
        self.diarization = diarization


class TranscriptDiarizationAssemblerProcessor(Processor):
    """
    Assemble transcript with diarization results by applying speaker assignments
    """

    INPUT_TYPE = TranscriptDiarizationAssemblerInput
    OUTPUT_TYPE = Transcript

    async def _push(self, data: TranscriptDiarizationAssemblerInput):
        result = await self._assemble(data)
        if result:
            await self.emit(result)

    async def _assemble(self, data: TranscriptDiarizationAssemblerInput):
        """Apply diarization to transcript words"""
        if not data.diarization:
            self.log.info("No diarization data provided, returning original transcript")
            return data.transcript

        # Reuse logic from AudioDiarizationProcessor
        processor = AudioDiarizationProcessor()
        words = data.transcript.words
        processor.assign_speaker(words, data.diarization)

        self.log.info(f"Applied diarization to {len(words)} words")
        return data.transcript
