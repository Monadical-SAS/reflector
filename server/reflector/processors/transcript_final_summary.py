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
    TITLE_TASK = "title"
    SUMMARY_TASK = "summary"

    SUMMARY_PROMPT = """
        Provide a concise bullet-point summary of the following text. Be sure
        to include the important things from the text.
    """
    TITLE_PROMPT = """
        Combine the following individual titles into one single title that
        condenses the essence of all titles.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance()
        self.final_summary_schema = {
            "type": "object",
            "properties": {"summary": {"type": "string"}},
        }
        self.final_title_schema = {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        }

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def _get_title(self):
        accumulated_titles = ". ".join([chunk.title for chunk in self.chunks])

        self.logger.info(f"Smoothing out title of length {len(accumulated_titles)}")
        title_result = await retry(self.llm.generate)(
            prompt=self.TITLE_PROMPT,
            text=accumulated_titles,
            task=self.TITLE_TASK,
            schema=self.final_title_schema,
            logger=self.logger,
        )
        return title_result

    async def _get_summary(self):
        accumulated_summary = " ".join([chunk.summary for chunk in self.chunks])

        self.logger.info(f"Smoothing out {len(accumulated_summary)} length summary")
        summary_result = await retry(self.llm.generate)(
            prompt=self.SUMMARY_PROMPT,
            text=accumulated_summary,
            task=self.SUMMARY_TASK,
            schema=self.final_summary_schema,
            logger=self.logger,
        )
        return summary_result

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        title_result = await self._get_title()
        summary_result = await self._get_summary()

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        final_summary = FinalSummary(
            title=title_result["title"],
            summary=summary_result["summary"],
            duration=duration,
        )
        await self.emit(final_summary)
