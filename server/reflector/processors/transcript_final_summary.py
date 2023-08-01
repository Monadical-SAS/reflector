from reflector.processors.base import Processor
from reflector.processors.types import TitleSummary, FinalSummary


class TranscriptFinalSummaryProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalSummary

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        # FIXME improve final summary
        result = "\n".join([chunk.summary for chunk in self.chunks])
        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        await self.emit(FinalSummary(summary=result, duration=duration))
