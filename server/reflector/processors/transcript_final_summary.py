from typing import Callable

import nltk
from pydantic.typing import List
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
    nltk.download("punkt", quiet=True)

    # Generation configurations
    summary_gen_cfg = GenerationConfig(
        max_new_tokens=1000, num_beams=3, use_cache=True, temperature=0.3
    )
    title_gen_cfg = GenerationConfig(
        max_new_tokens=200, num_beams=5, use_cache=True, temperature=0.5
    )

    # Prompt instructions
    FINAL_SUMMARY_PROMPT = """
        Take the key ideas and takeaways from the text and create a short summary.
         Be sure to keep the length of the response to a minimum. Do not include
         trivial information in the summary.
    """
    FINAL_TITLE_PROMPT = """
        Combine the following individual titles into one single short title that
        condenses the essence of all titles.
    """

    # Generation schema
    final_summary_schema = {
        "type": "object",
        "properties": {"summary": {"type": "string"}},
    }
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
        self.prompt_template = LLMPromptTemplate.template
        self.tokenizer = AutoTokenizer.from_pretrained(self.llm.name)

    def _create_prompt(self, user_prompt: str, text: str) -> str:
        """
        Create a consumable prompt based on the prompt template
        """
        return self.prompt_template.format(user_prompt=user_prompt, text=text)

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    def _split_corpus(
        self, tokenizer: Callable, corpus: str, token_threshold: int = 800
    ) -> List[str]:
        """
        Split the input to the LLM due to CUDA memory limitations and LLM context window
        restrictions.

        Accumulate tokens from full sentences till threshold and yield accumulated
        tokens. Reset accumulation and repeat process.
        """
        accumulated_tokens = []
        accumulated_sentences = []
        accumulated_token_count = 0
        corpus_sentences = nltk.sent_tokenize(corpus)

        for sentence in corpus_sentences:
            tokens = tokenizer.tokenize(sentence)
            if accumulated_token_count + len(tokens) <= token_threshold:
                accumulated_token_count += len(tokens)
                accumulated_tokens.extend(tokens)
                accumulated_sentences.append(sentence)
            else:
                yield "".join(accumulated_sentences)
                accumulated_token_count = len(tokens)
                accumulated_tokens = tokens
                accumulated_sentences = [sentence]

        if accumulated_tokens:
            yield " ".join(accumulated_sentences)

    async def _get_title(self):
        accumulated_titles = ". ".join([chunk.title for chunk in self.chunks])

        self.logger.info(f"Smoothing out title of length {len(accumulated_titles)}")
        title_result = await retry(self.llm.generate)(
            prompt=self.FINAL_TITLE_PROMPT,
            schema=self.final_title_schema,
            logger=self.logger,
        )
        return title_result

    async def _get_summary(self):
        accumulated_summary = " ".join([chunk.summary for chunk in self.chunks])

        self.logger.info(f"Smoothing out {len(accumulated_summary)} length summary")
        summary_result = await retry(self.llm.generate)(
            prompt=self.FINAL_SUMMARY_PROMPT,
            text=accumulated_summary,
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
