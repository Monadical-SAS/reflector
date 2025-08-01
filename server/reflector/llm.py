from typing import Type, TypeVar

from llama_index.core import Settings
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.response_synthesizers import TreeSummarize
from llama_index.llms.openai_like import OpenAILike
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

STRUCTURED_RESPONSE_PROMPT_TEMPLATE = """
Based on the following analysis, provide the information in the requested JSON format:

Analysis:
{analysis}

{format_instructions}
"""


class LLM:
    def __init__(self, settings, temperature: float = 0.4, max_tokens: int = 2048):
        self.settings_obj = settings
        self.model_name = settings.LLM_MODEL
        self.url = settings.LLM_URL
        self.api_key = settings.LLM_API_KEY
        self.context_window = settings.LLM_CONTEXT_WINDOW
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Configure llamaindex Settings
        self._configure_llamaindex()

    def _configure_llamaindex(self):
        """Configure llamaindex Settings with OpenAILike LLM"""
        Settings.llm = OpenAILike(
            model=self.model_name,
            api_base=self.url,
            api_key=self.api_key,
            context_window=self.context_window,
            is_chat_model=True,
            is_function_calling_model=False,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )

    async def get_response(
        self, prompt: str, texts: list[str], tone_name: str | None = None
    ) -> str:
        """Get a text response using TreeSummarize for non-function-calling models"""
        summarizer = TreeSummarize(verbose=False)
        response = await summarizer.aget_response(prompt, texts, tone_name=tone_name)
        return str(response).strip()

    async def get_structured_response(
        self,
        prompt: str,
        texts: list[str],
        output_cls: Type[T],
        tone_name: str | None = None,
    ) -> T:
        """Get structured output from LLM for non-function-calling models"""
        summarizer = TreeSummarize(verbose=True)
        response = await summarizer.aget_response(prompt, texts, tone_name=tone_name)

        output_parser = PydanticOutputParser(output_cls)

        program = LLMTextCompletionProgram.from_defaults(
            output_parser=output_parser,
            prompt_template_str=STRUCTURED_RESPONSE_PROMPT_TEMPLATE,
            verbose=False,
        )

        format_instructions = output_parser.format(
            "Please structure the above information in the following JSON format:"
        )

        output = await program.acall(
            analysis=str(response), format_instructions=format_instructions
        )

        return output
