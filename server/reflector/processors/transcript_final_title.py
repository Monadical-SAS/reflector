from transformers import AutoTokenizer
from transformers.generation import GenerationConfig

from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.types import FinalTitle, LLMPromptTemplate, TitleSummary
from reflector.utils.retry import retry


class TranscriptFinalTitleProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalTitle

    # Generation configurations
    title_gen_cfg = GenerationConfig(
        max_new_tokens=200, num_beams=5, use_cache=True, temperature=0.5
    )

    # Prompt instructions
    FINAL_TITLE_PROMPT = """
        Combine the following individual titles into one single short title that
        condenses the essence of all titles.
    """

    # Generation schema
    final_title_schema = {
        "type": "object",
        "properties": {"title": {"type": "string"}},
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance()
        # TODO: Once we have the option to pass LLM as constructor param,
        # choose the corresponding prompt template
        self.prompt_template = LLMPromptTemplate().template
        self.tokenizer = AutoTokenizer.from_pretrained("lmsys/vicuna-13b-v1.5")

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_title(self, text: str) -> dict:
        chunks = list(self.split_corpus(self.tokenizer, text))

        if len(chunks) == 1:
            self.logger.info(f"Smoothing out {len(text)} titles")
            prompt = self.llm.create_prompt(
                user_prompt=self.FINAL_TITLE_PROMPT, text=chunks[0]
            )
            title_result = await retry(self.llm.generate)(
                prompt=prompt, schema=self.final_title_schema, logger=self.logger
            )
            return title_result
        else:
            accumulated_titles = []
            for chunk in chunks:
                prompt = self.llm.create_prompt(
                    user_prompt=self.FINAL_TITLE_PROMPT, text=chunk
                )
                title_result = await retry(self.llm.generate)(
                    prompt=prompt, schema=self.final_title_schema, logger=self.logger
                )
                accumulated_titles.append(title_result)
            titles = ".".join([chunk.title for chunk in self.chunks])

            return await self.get_title(titles)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_titles = ".".join([chunk.title for chunk in self.chunks])
        title_result = await self.get_title(accumulated_titles)

        final_title = FinalTitle(title=title_result["title"])
        await self.emit(final_title)
