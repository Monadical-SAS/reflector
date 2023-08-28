from transformers import AutoTokenizer
from transformers.generation import GenerationConfig

from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.types import FinalSummary, LLMPromptTemplate, TitleSummary
from reflector.utils.retry import retry


class TranscriptFinalSummaryProcessor(Processor):
    """
    Assemble all summary into a line-based json
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalSummary

    # Generation configuration
    summary_gen_cfg = GenerationConfig(
        max_new_tokens=1300, num_beams=3, use_cache=True, temperature=0.3
    )

    # Prompt instructions
    FINAL_SUMMARY_PROMPT = """
        Take the key ideas and takeaways from the text and create a short summary.
         Be sure to keep the length of the response to a minimum. Do not include
         trivial information in the summary.
    """

    # Generation schema
    final_summary_schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []
        self.llm = LLM.get_instance()
        # TODO: Once we have the option to pass LLM as constructor param,
        # choose the corresponding prompt template
        self.prompt_template = LLMPromptTemplate.template
        self.tokenizer = AutoTokenizer.from_pretrained("lmsys/vicuna-13b-v1.5")

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_long_summary(self, text: str) -> str:
        chunks = list(self.split_corpus(self.tokenizer, text))

        accumulated_summaries = ""
        for chunk in chunks:
            prompt = self.llm.create_prompt(
                user_prompt=self.FINAL_SUMMARY_PROMPT, text=chunk
            )
            summary_result = await retry(self.llm.generate)(
                prompt=prompt, schema=self.final_summary_schema, logger=self.logger
            )
            accumulated_summaries += summary_result["summary"]

        return accumulated_summaries

    async def tree_summarizer(self, text: str) -> dict:
        chunks = list(self.split_corpus(self.tokenizer, text))

        if len(chunks) == 1:
            self.logger.info(f"Smoothing out {len(text)} length summary")
            prompt = self.llm.create_prompt(
                user_prompt=self.FINAL_SUMMARY_PROMPT, text=chunks[0]
            )
            summary_result = await retry(self.llm.generate)(
                prompt=prompt, schema=self.final_summary_schema, logger=self.logger
            )
            return summary_result
        else:
            accumulated_summaries = ""
            for chunk in chunks:
                prompt = self.llm.create_prompt(
                    user_prompt=self.FINAL_SUMMARY_PROMPT, text=chunk
                )
                summary_result = await retry(self.llm.generate)(
                    prompt=prompt, schema=self.final_summary_schema, logger=self.logger
                )
                accumulated_summaries += summary_result["summary"]

            return await self.tree_summarizer(accumulated_summaries)

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_summaries = " ".join([chunk.summary for chunk in self.chunks])
        summary_result = await self.tree_summarizer(accumulated_summaries)

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        final_summary = FinalSummary(
            summary=summary_result["summary"],
            duration=duration,
        )
        await self.emit(final_summary)
