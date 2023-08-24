from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.types import FinalSummary, TitleSummary
from reflector.utils.retry import retry


class TranscriptFinalSummaryProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalSummary
    TASK = "summary"

    PROMPT = """
        Provide a concise bullet-point summary of the following text. Be sure
        to include the important things from the text.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance()
        self.final_summary_schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
        }

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_summary = " ".join([chunk.summary for chunk in self.chunks])
        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        self.logger.info(f"Smoothing out {len(accumulated_summary)} length summary")
        result = await retry(self.llm.generate)(
            prompt=self.PROMPT,
            text=accumulated_summary,
            task=self.TASK,
            schema=self.final_summary_schema,
            logger=self.logger,
        )
        await self.emit(FinalSummary(summary=result["summary"], duration=duration))
