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
        self.params = LLMTaskParams.get_instance(self.TASK).task_params

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_title(self, text: str) -> dict:
        """
        Generate a title for the whole recording
        """
        chunks = list(self.llm.split_corpus(corpus=text, llm_params=self.params))

        if len(chunks) == 1:
            chunk = chunks[0]
            prompt = self.llm.create_prompt(instruct=self.params.instruct, text=chunk)
            title_result = await self.llm.generate(
                prompt=prompt,
                gen_schema=self.params.gen_schema,
                gen_cfg=self.params.gen_cfg,
                logger=self.logger,
            )
            return title_result
        else:
            accumulated_titles = ""
            for chunk in chunks:
                prompt = self.llm.create_prompt(
                    instruct=self.params.instruct, text=chunk
                )
                title_result = await self.llm.generate(
                    prompt=prompt,
                    gen_schema=self.params.gen_schema,
                    gen_cfg=self.params.gen_cfg,
                    logger=self.logger,
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
