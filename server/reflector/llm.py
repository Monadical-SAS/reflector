import json
import logging
from typing import Callable, Type, TypeVar

from llama_index.core import Settings
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.response_synthesizers import TreeSummarize
from llama_index.llms.openai_like import OpenAILike
from pydantic import BaseModel, ValidationError

T = TypeVar("T", bound=BaseModel)
RawResponseCallback = Callable[[str], None] | None

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
        self.logger = logging.getLogger(__name__)

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
        """Get structured output from LLM with parse error recovery"""
        last_error = None
        raw_response_capture = {"value": None}

        for attempt in range(self.settings_obj.LLM_PARSE_RETRY_ATTEMPTS):
            try:
                enhanced_prompt = prompt

                if last_error:
                    error_msg = self._format_parse_error_feedback(last_error)
                    enhanced_prompt += (
                        f"\n\nYour previous response had errors:\n{error_msg}\n"
                        "Please return valid JSON fixing all these issues."
                    )

                return await self._do_structured_call(
                    enhanced_prompt,
                    texts,
                    output_cls,
                    tone_name,
                    on_response=lambda raw: raw_response_capture.__setitem__(
                        "value", raw
                    ),
                )

            except (ValidationError, json.JSONDecodeError, ValueError) as e:
                last_error = e
                error_msg = (
                    f"LLM parse error (attempt {attempt + 1}/"
                    f"{self.settings_obj.LLM_PARSE_RETRY_ATTEMPTS}): "
                    f"{type(e).__name__}: {str(e)}"
                )
                if raw_response_capture["value"]:
                    error_msg += (
                        f"\nRaw response: {raw_response_capture['value'][:500]}"
                    )
                self.logger.error(error_msg)

        raise last_error

    async def _do_structured_call(
        self,
        prompt: str,
        texts: list[str],
        output_cls: Type[T],
        tone_name: str | None = None,
        on_response: RawResponseCallback = None,
    ) -> T:
        """Core structured response logic"""
        summarizer = TreeSummarize(verbose=False)
        response = await summarizer.aget_response(prompt, texts, tone_name=tone_name)
        raw = str(response)

        if on_response:
            on_response(raw)

        output_parser = PydanticOutputParser(output_cls)
        program = LLMTextCompletionProgram.from_defaults(
            output_parser=output_parser,
            prompt_template_str=STRUCTURED_RESPONSE_PROMPT_TEMPLATE,
            verbose=False,
        )
        format_instructions = output_parser.format(
            "Please structure the above information in the following JSON format:"
        )
        return await program.acall(
            analysis=raw, format_instructions=format_instructions
        )

    def _format_parse_error_feedback(self, error: Exception) -> str:
        """Format parse error into feedback for LLM"""
        if isinstance(error, ValidationError):
            error_messages = []
            for err in error.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                error_messages.append(f"- {err['msg']} in field '{field}'")
            return "Schema validation errors:\n" + "\n".join(error_messages)

        elif isinstance(error, json.JSONDecodeError):
            return f"Invalid JSON syntax at position {error.pos}: {error.msg}"

        else:
            return f"Parse error: {str(error)}"
