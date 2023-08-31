from reflector.llm import LLM, LLMParams
from reflector.processors.base import Processor
from reflector.processors.types import FinalSummary, TitleSummary


class TranscriptFinalLongSummaryProcessor(Processor):
    """
    Get the final long summary
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalSummary
    TASK = "summary"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance(model_name="lmsys/vicuna-13b-v1.5")
        self.params = LLMParams(self.TASK)

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_long_summary(self, text: str) -> str:
        chunks = list(self.llm.split_corpus(corpus=text))

        accumulated_summaries = ""
        for chunk in chunks:
            summary_result = await self.llm.get_response(
                text=chunk,
                params=self.params,
            )
            accumulated_summaries += summary_result["summary"]

        return accumulated_summaries

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_summaries = " ".join([chunk.summary for chunk in self.chunks])
        summary_result = await self.get_long_summary(accumulated_summaries)

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        final_summary = FinalSummary(
            summary=summary_result["summary"],
            duration=duration,
        )
        await self.emit(final_summary)
