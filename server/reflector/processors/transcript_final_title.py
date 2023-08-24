from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.types import FinalTitle, TitleSummary
from reflector.utils.retry import retry


class TranscriptFinalTitleProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalTitle
    TASK = "title"

    PROMPT = """
        Combine the following individual titles into one single title that
        condenses the essence of all titles.

    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance()
        self.final_title_schema = {
            "type": "object",
            "properties": {"title": {"type": "string"}},
        }

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_titles = ". ".join([chunk.title for chunk in self.chunks])

        self.logger.info(f"Smoothing out title of length {len(accumulated_titles)}")
        result = await retry(self.llm.generate)(
            prompt=self.PROMPT,
            text=accumulated_titles,
            task=self.TASK,
            schema=self.final_title_schema,
            logger=self.logger,
        )
        await self.emit(FinalTitle(title=result["title"]))
