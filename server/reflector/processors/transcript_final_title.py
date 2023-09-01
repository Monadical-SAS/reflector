from reflector.llm import LLM, LLMTaskParams
from reflector.processors.base import Processor
from reflector.processors.types import FinalTitle, TitleSummary


class TranscriptFinalTitleProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalTitle
    TASK = "final_title"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance("lmsys/vicuna-13b-v1.5")
        self.params = LLMTaskParams.get_instance(self.TASK)

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_title(self, text: str) -> dict:
        """
        Generate a title for the whole recording
        """
        chunks = list(self.llm.split_corpus(corpus=text, params=self.params))

        if len(chunks) == 1:
            self.logger.info(f"Smoothing out {len(text)} length summary")
            chunk = chunks[0]
            title_result = await self.llm.get_response(
                text=chunk, llm_params=self.params, logger=self.logger
            )
            return title_result
        else:
            accumulated_titles = ""
            for chunk in chunks:
                title_result = await self.llm.get_response(
                    text=chunk, llm_params=self.params, logger=self.logger
                )
                accumulated_titles += title_result["summary"]

            return await self.get_title(accumulated_titles)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_titles = ".".join([chunk.title for chunk in self.chunks])
        title_result = await self.get_title(accumulated_titles)

        final_title = FinalTitle(title=title_result["title"])
        print("****************")
        print("FINAL TITLE", final_title.title)
        print("****************")
        await self.emit(final_title)
