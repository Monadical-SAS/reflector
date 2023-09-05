from reflector.llm import LLM, LLMTaskParams
from reflector.processors.base import Processor
from reflector.processors.types import FinalLongSummary, TitleSummary


class TranscriptFinalLongSummaryProcessor(Processor):
    """
    Get the final long summary
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalLongSummary
    TASK = "final_long_summary"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance(model_name="lmsys/vicuna-13b-v1.5")
        self.params = LLMTaskParams.get_instance(self.TASK).task_params

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_long_summary(self, text: str) -> str:
        """
        Generate a long version of the final summary
        """
        self.logger.info(f"Smoothing out {len(text)} length summary to a long summary")
        chunks = list(self.llm.split_corpus(corpus=text, task_params=self.params))

        accumulated_summaries = ""
        for chunk in chunks:
            prompt = self.llm.create_prompt(instruct=self.params.instruct, text=chunk)
            summary_result = await self.llm.generate(
                prompt=prompt,
                gen_schema=self.params.gen_schema,
                gen_cfg=self.params.gen_cfg,
                logger=self.logger,
            )
            accumulated_summaries += summary_result["long_summary"]

        return accumulated_summaries

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_summaries = " ".join([chunk.summary for chunk in self.chunks])
        long_summary = await self.get_long_summary(accumulated_summaries)

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        final_long_summary = FinalLongSummary(
            long_summary=long_summary,
            duration=duration,
        )
        await self.emit(final_long_summary)
