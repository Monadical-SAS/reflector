import logging
from contextvars import ContextVar
from typing import Generic, Type, TypeVar
from uuid import uuid4

from llama_index.core import Settings
from llama_index.core.output_parsers import PydanticOutputParser
from llama_index.core.response_synthesizers import TreeSummarize
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.llms.openai_like import OpenAILike
from pydantic import BaseModel, ValidationError
from workflows.errors import WorkflowTimeoutError

from reflector.utils.retry import retry

T = TypeVar("T", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

# Session ID for LiteLLM request grouping - set per processing run
llm_session_id: ContextVar[str | None] = ContextVar("llm_session_id", default=None)

logger = logging.getLogger(__name__)

STRUCTURED_RESPONSE_PROMPT_TEMPLATE = """
Based on the following analysis, provide the information in the requested JSON format:

Analysis:
{analysis}

{format_instructions}
"""


class LLMParseError(Exception):
    """Raised when LLM output cannot be parsed after retries."""

    def __init__(self, output_cls: Type[BaseModel], error_msg: str, attempts: int):
        self.output_cls = output_cls
        self.error_msg = error_msg
        self.attempts = attempts
        super().__init__(
            f"Failed to parse {output_cls.__name__} after {attempts} attempts: {error_msg}"
        )


class ExtractionDone(Event):
    """Event emitted when LLM JSON formatting completes."""

    output: str


class ValidationErrorEvent(Event):
    """Event emitted when validation fails."""

    error: str
    wrong_output: str


class StructuredOutputWorkflow(Workflow, Generic[OutputT]):
    """Workflow for structured output extraction with validation retry.

    This workflow handles parse/validation retries only. Network error retries
    are handled internally by Settings.llm (OpenAILike max_retries=3).
    The caller should NOT wrap this workflow in additional retry logic.
    """

    def __init__(
        self,
        output_cls: Type[OutputT],
        max_retries: int = 3,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.output_cls: Type[OutputT] = output_cls
        self.max_retries = max_retries
        self.output_parser = PydanticOutputParser(output_cls)

    @step
    async def extract(
        self, ctx: Context, ev: StartEvent | ValidationErrorEvent
    ) -> StopEvent | ExtractionDone:
        """Extract structured data from text using two-step LLM process.

        Step 1 (first call only): TreeSummarize generates text analysis
        Step 2 (every call): Settings.llm.acomplete formats analysis as JSON
        """
        current_retries = await ctx.store.get("retries", default=0)
        await ctx.store.set("retries", current_retries + 1)

        if current_retries >= self.max_retries:
            last_error = await ctx.store.get("last_error", default=None)
            logger.error(
                f"Max retries ({self.max_retries}) reached for {self.output_cls.__name__}"
            )
            return StopEvent(result={"error": last_error, "attempts": current_retries})

        if isinstance(ev, StartEvent):
            # First call: run TreeSummarize to get analysis, store in context
            prompt = ev.get("prompt")
            texts = ev.get("texts")
            tone_name = ev.get("tone_name")
            if not prompt or not isinstance(texts, list):
                raise ValueError(
                    "StartEvent must contain 'prompt' (str) and 'texts' (list)"
                )

            summarizer = TreeSummarize(verbose=False)
            analysis = await summarizer.aget_response(
                prompt, texts, tone_name=tone_name
            )
            await ctx.store.set("analysis", str(analysis))
            reflection = ""
        else:
            # Retry: reuse analysis from context
            analysis = await ctx.store.get("analysis")
            if not analysis:
                raise RuntimeError("Internal error: analysis not found in context")

            wrong_output = ev.wrong_output
            if len(wrong_output) > 2000:
                wrong_output = wrong_output[:2000] + "... [truncated]"
            reflection = (
                f"\n\nYour previous response could not be parsed:\n{wrong_output}\n\n"
                f"Error:\n{ev.error}\n\n"
                "Please try again. Return ONLY valid JSON matching the schema above, "
                "with no markdown formatting or extra text."
            )

        # Step 2: Format analysis as JSON using LLM completion
        format_instructions = self.output_parser.format(
            "Please structure the above information in the following JSON format:"
        )

        json_prompt = STRUCTURED_RESPONSE_PROMPT_TEMPLATE.format(
            analysis=analysis,
            format_instructions=format_instructions + reflection,
        )

        # Network retries handled by OpenAILike (max_retries=3)
        response = await Settings.llm.acomplete(json_prompt)
        return ExtractionDone(output=response.text)

    @step
    async def validate(
        self, ctx: Context, ev: ExtractionDone
    ) -> StopEvent | ValidationErrorEvent:
        """Validate extracted output against Pydantic schema."""
        raw_output = ev.output
        retries = await ctx.store.get("retries", default=0)

        try:
            parsed = self.output_parser.parse(raw_output)
            if retries > 1:
                logger.info(
                    f"LLM parse succeeded on attempt {retries}/{self.max_retries} "
                    f"for {self.output_cls.__name__}"
                )
            return StopEvent(result={"success": parsed})

        except (ValidationError, ValueError) as e:
            error_msg = self._format_error(e, raw_output)
            await ctx.store.set("last_error", error_msg)

            logger.error(
                f"LLM parse error (attempt {retries}/{self.max_retries}): "
                f"{type(e).__name__}: {e}\nRaw response: {raw_output[:500]}"
            )

            return ValidationErrorEvent(
                error=error_msg,
                wrong_output=raw_output,
            )

    def _format_error(self, error: Exception, raw_output: str) -> str:
        """Format error for LLM feedback."""
        if isinstance(error, ValidationError):
            error_messages = []
            for err in error.errors():
                field = ".".join(str(loc) for loc in err["loc"])
                error_messages.append(f"- {err['msg']} in field '{field}'")
            return "Schema validation errors:\n" + "\n".join(error_messages)
        else:
            return f"Parse error: {str(error)}"


class LLM:
    def __init__(self, settings, temperature: float = 0.4, max_tokens: int = 2048):
        self.settings_obj = settings
        self.model_name = settings.LLM_MODEL
        self.url = settings.LLM_URL
        self.api_key = settings.LLM_API_KEY
        self.context_window = settings.LLM_CONTEXT_WINDOW
        self.temperature = temperature
        self.max_tokens = max_tokens

        self._configure_llamaindex()

    def _configure_llamaindex(self):
        """Configure llamaindex Settings with OpenAILike LLM"""
        session_id = llm_session_id.get() or f"fallback-{uuid4().hex}"

        Settings.llm = OpenAILike(
            model=self.model_name,
            api_base=self.url,
            api_key=self.api_key,
            context_window=self.context_window,
            is_chat_model=True,
            is_function_calling_model=False,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            additional_kwargs={"extra_body": {"litellm_session_id": session_id}},
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
        """Get structured output from LLM with validation retry via Workflow."""

        async def run_workflow():
            workflow = StructuredOutputWorkflow(
                output_cls=output_cls,
                max_retries=self.settings_obj.LLM_PARSE_MAX_RETRIES + 1,
                timeout=120,
            )

            result = await workflow.run(
                prompt=prompt,
                texts=texts,
                tone_name=tone_name,
            )

            if "error" in result:
                error_msg = result["error"] or "Max retries exceeded"
                raise LLMParseError(
                    output_cls=output_cls,
                    error_msg=error_msg,
                    attempts=result.get("attempts", 0),
                )

            return result["success"]

        return await retry(run_workflow)(
            retry_attempts=3,
            retry_backoff_interval=1.0,
            retry_backoff_max=30.0,
            retry_ignore_exc_types=(WorkflowTimeoutError,),
        )
