from textwrap import dedent

from llama_index.core import Settings
from llama_index.core.response_synthesizers import TreeSummarize
from llama_index.llms.openai_like import OpenAILike

from reflector.llm.openai_llm import OpenAILLM
from reflector.processors.base import Processor
from reflector.processors.types import FinalTitle, TitleSummary
from reflector.settings import settings

TITLE_PROMPT = dedent(
    """
    Generate a concise title for this meeting based on the following topic titles.
    Ignore casual conversation, greetings, or administrative matters.

    The title must:
    - Be maximum 10 words
    - Use noun phrases when possible (e.g., "Q1 Budget Review" not "Reviewing the Q1 Budget")
    - Avoid generic terms like "Team Meeting" or "Discussion"

    If multiple unrelated topics were discussed, prioritize the most significant one.
    or create a compound title (e.g., "Product Launch and Budget Planning").

    <topics_discussed>
    {titles}
    </topics_discussed>

    Do not explain, just output the meeting title as a single line.
    """
).strip()


class TranscriptFinalTitleProcessor(Processor):
    """
    Generate a final title from topic titles using LlamaIndex
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalTitle

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chunks: list[TitleSummary] = []

        # Initialize OpenAI-compatible LLM
        llm = OpenAILLM(config_prefix="SUMMARY", settings=settings)

        # Configure LlamaIndex settings
        Settings.llm = OpenAILike(
            model=llm.model_name,
            api_base=llm.url,
            api_key=llm.api_key,
            context_window=settings.SUMMARY_LLM_CONTEXT_SIZE_TOKENS,
            is_chat_model=True,
            is_function_calling_model=False,
            temperature=0.5,
            max_tokens=200,
        )

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_title(self, accumulated_titles: str) -> str:
        """
        Generate a title for the whole recording using LlamaIndex
        """
        prompt = TITLE_PROMPT.format(titles=accumulated_titles)
        summarizer = TreeSummarize(verbose=False)
        response = await summarizer.aget_response(
            prompt,
            [accumulated_titles],
            tone_name="Title generator",
        )

        self.logger.info(f"Generated title response: {response}")

        return str(response).strip()

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        accumulated_titles = "\n".join([f"- {chunk.title}" for chunk in self.chunks])
        title = await self.get_title(accumulated_titles)
        title = self._clean_title(title)

        final_title = FinalTitle(title=title)
        await self.emit(final_title)

    def _clean_title(self, title: str) -> str:
        title = title.strip("\"'")
        words = title.split()
        if words:
            words = [
                word.capitalize() if i == 0 or len(word) > 3 else word.lower()
                for i, word in enumerate(words)
            ]
            title = " ".join(words)
        return title
