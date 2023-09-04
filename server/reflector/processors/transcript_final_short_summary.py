from reflector.llm import LLM, LLMTaskParams
from reflector.processors.base import Processor
from reflector.processors.types import FinalShortSummary, TitleSummary


class TranscriptFinalShortSummaryProcessor(Processor):
    """
    Get the final summary using a tree summarizer
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalShortSummary
    TASK = "final_short_summary"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance(model_name="lmsys/vicuna-13b-v1.5")
        self.params = LLMTaskParams.get_instance(self.TASK)

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_short_summary(self, text: str) -> dict:
        """
        Generata a short summary using tree summarizer
        """
        self.logger.info(f"Smoothing out {len(text)} length summary to a short summary")
        chunks = list(self.llm.split_corpus(corpus=text, llm_params=self.params))

        if len(chunks) == 1:
            chunk = chunks[0]
            summary_result = await self.llm.get_response(
                text=chunk, llm_params=self.params, logger=self.logger
            )
            return summary_result
        else:
            accumulated_summaries = ""
            for chunk in chunks:
                summary_result = await self.llm.get_response(
                    text=chunk, llm_params=self.params, logger=self.logger
                )
                accumulated_summaries += summary_result["short_summary"]

            return await self.get_short_summary(accumulated_summaries)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_summaries = " ".join([chunk.summary for chunk in self.chunks])
        short_summary_result = await self.get_short_summary(accumulated_summaries)

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        final_summary = FinalShortSummary(
            short_summary=short_summary_result["short_summary"],
            duration=duration,
        )
        print("****************")
        print("FINAL SHORT SUMMARY", final_summary.short_summary)
        print("****************")
        await self.emit(final_summary)
