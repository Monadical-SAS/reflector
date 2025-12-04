import logging
from typing import Type, TypeVar

import httpx
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

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable based on error type and status code"""
        if isinstance(
            error,
            (
                asyncio.TimeoutError,
                httpx.TimeoutException,  # Base class for all httpx timeouts
                httpx.ConnectError,  # Connection failures
                httpx.NetworkError,  # Network unreachable, DNS failures
                httpx.RemoteProtocolError,  # Malformed HTTP response
                httpx.ReadError,  # Connection broken while reading
                httpx.WriteError,  # Connection broken while writing
            ),
        ):
            return True

        if isinstance(error, httpx.HTTPStatusError):
            retryable_codes = [429, 500, 502, 503, 504]
            return error.response.status_code in retryable_codes

        # Don't retry auth errors, bad requests, or unknown errors
        return False

    def _get_retry_decorator(self):
        """Create retry decorator with current settings"""

        def should_retry(retry_state):
            """Custom retry predicate that checks if error is retryable"""
            if retry_state.outcome.failed:
                error = retry_state.outcome.exception()
                return self._is_retryable_error(error)
            return False

        return retry(
            retry=should_retry,
            stop=stop_after_attempt(self.settings_obj.LLM_RETRY_NETWORK_ATTEMPTS),
            wait=wait_exponential_jitter(
                initial=self.settings_obj.LLM_RETRY_WAIT_INITIAL,
                max=self.settings_obj.LLM_RETRY_WAIT_MAX,
            ),
            before=before_log(self.logger, logging.INFO),
            after=after_log(self.logger, logging.INFO),
            reraise=True,
        )

    async def get_response(
        self, prompt: str, texts: list[str], tone_name: str | None = None
    ) -> str:
        """Get a text response using TreeSummarize for non-function-calling models with retry logic"""
        if not self.settings_obj.LLM_RETRY_ENABLED:
            summarizer = TreeSummarize(verbose=False)
            response = await summarizer.aget_response(
                prompt, texts, tone_name=tone_name
            )
            return str(response).strip()

        retry_decorator = self._get_retry_decorator()

        @retry_decorator
        async def _get_response_with_retry():
            summarizer = TreeSummarize(verbose=False)
            response = await summarizer.aget_response(
                prompt, texts, tone_name=tone_name
            )
            return str(response).strip()

        try:
            return await asyncio.wait_for(
                _get_response_with_retry(),
                timeout=self.settings_obj.LLM_RETRY_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self.logger.error(
                f"LLM request timed out after {self.settings_obj.LLM_RETRY_TIMEOUT}s"
            )
            raise
        except Exception as e:
            if not self._is_retryable_error(e):
                self.logger.error(
                    f"Non-retryable error in get_response: {type(e).__name__}: {e}"
                )
            raise

    async def get_structured_response(
        self,
        prompt: str,
        texts: list[str],
        output_cls: Type[T],
        tone_name: str | None = None,
    ) -> T:
        """Get structured output from LLM for non-function-calling models"""
        if not self.settings_obj.LLM_RETRY_ENABLED:
            return await self._get_structured_response_no_retry(
                prompt, texts, output_cls, tone_name
            )

        async def _get_structured_with_timeout():
            # Parse error handling loop
            last_error = None
            # Closure variable to capture raw response for error logging
            raw_response_capture = {"value": None}

            for attempt in range(self.settings_obj.LLM_RETRY_PARSE_ATTEMPTS):
                try:
                    enhanced_prompt = prompt

                    if last_error:
                        error_msg = self._format_parse_error_feedback(last_error)
                        enhanced_prompt += f"\n\nYour previous response had errors:\n{error_msg}\nPlease return valid JSON fixing all these issues."

                    retry_decorator = self._get_retry_decorator()

                    @retry_decorator
                    async def _get_structured_with_retry():
                        return await self._do_structured_call(
                            enhanced_prompt,
                            texts,
                            output_cls,
                            tone_name,
                            on_response=lambda raw: raw_response_capture.__setitem__(
                                "value", raw
                            ),
                        )

                    return await _get_structured_with_retry()

                except (ValidationError, json.JSONDecodeError, ValueError) as e:
                    last_error = e
                    error_msg = (
                        f"LLM parse error (attempt {attempt + 1}/{self.settings_obj.LLM_RETRY_PARSE_ATTEMPTS}): "
                        f"{type(e).__name__}: {str(e)}"
                    )
                    if raw_response_capture["value"]:
                        error_msg += (
                            f"\nRaw response: {raw_response_capture['value'][:500]}"
                        )
                    self.logger.error(error_msg)

            raise last_error

        try:
            return await asyncio.wait_for(
                _get_structured_with_timeout(),
                timeout=self.settings_obj.LLM_RETRY_TIMEOUT,
            )
        except asyncio.TimeoutError:
            self.logger.error(
                f"LLM request timed out after {self.settings_obj.LLM_RETRY_TIMEOUT}s"
            )
            raise

    async def _get_structured_response_no_retry(
        self,
        prompt: str,
        texts: list[str],
        output_cls: Type[T],
        tone_name: str | None = None,
    ) -> T:
        """Get structured output without retry logic (for when retry is disabled)"""
        return await self._do_structured_call(prompt, texts, output_cls, tone_name)

    async def _do_structured_call(
        self,
        prompt: str,
        texts: list[str],
        output_cls: Type[T],
        tone_name: str | None = None,
        on_response: RawResponseCallback = None,
    ) -> T:
        """Core structured response logic shared by retry and no-retry paths"""
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
            # Extract all validation errors with full detail
            error_messages = []
            for err in error.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                error_messages.append(f"- {err['msg']} in field '{field}'")
            return "Schema validation errors:\n" + "\n".join(error_messages)

        elif isinstance(error, json.JSONDecodeError):
            return f"Invalid JSON syntax at position {error.pos}: {error.msg}"
        try:
            output = await program.acall(
                analysis=str(response), format_instructions=format_instructions
            )
        except ValidationError as e:
            # Extract the raw JSON from the error details
            errors = e.errors()
            if errors and "input" in errors[0]:
                raw_json = errors[0]["input"]
                logger.error(
                    f"JSON validation failed for {output_cls.__name__}. "
                    f"Full raw JSON output:\n{raw_json}\n"
                    f"Validation errors: {errors}"
                )
            else:
                logger.error(
                    f"JSON validation failed for {output_cls.__name__}. "
                    f"Validation errors: {errors}"
                )
            raise

        else:
            return f"Parse error: {str(error)}"
