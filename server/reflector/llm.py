import logging
from typing import Generic, Type, TypeVar

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

T = TypeVar("T", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

logger = logging.getLogger(__name__)


class ExtractionDone(Event):
    """Event emitted when LLM extraction completes."""

    output: str
    prompt: str
    texts: list[str]
    tone_name: str | None


class ValidationErrorEvent(Event):
    """Event emitted when validation fails."""

    error: str
    wrong_output: str
    prompt: str
    texts: list[str]
    tone_name: str | None


class StructuredOutputWorkflow(Workflow, Generic[OutputT]):
    """Workflow for structured output extraction with validation retry."""

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
        """Extract structured data from text using LLM."""
        current_retries = await ctx.get("retries", default=0)

        if current_retries >= self.max_retries:
            last_error = await ctx.get("last_error", default=None)
            logger.error(
                f"Max retries ({self.max_retries}) reached for {self.output_cls.__name__}"
            )
            return StopEvent(result={"error": last_error})

        await ctx.set("retries", current_retries + 1)

        if isinstance(ev, StartEvent):
            prompt = ev.get("prompt")
            texts = ev.get("texts")
            tone_name = ev.get("tone_name")
            reflection = ""
        else:
            prompt = ev.prompt
            texts = ev.texts
            tone_name = ev.tone_name
            # Truncate wrong output to avoid blowing up context
            wrong_output = ev.wrong_output
            if len(wrong_output) > 2000:
                wrong_output = wrong_output[:2000] + "... [truncated]"
            reflection = (
                f"\n\nYour previous response could not be parsed:\n{wrong_output}\n\n"
                f"Error:\n{ev.error}\n\n"
                "Please try again. Return ONLY valid JSON matching the schema above, "
                "with no markdown formatting or extra text."
            )

        full_prompt = prompt + reflection

        summarizer = TreeSummarize(verbose=False)
        response = await summarizer.aget_response(
            full_prompt, texts, tone_name=tone_name
        )

        output = str(response)

        return ExtractionDone(
            output=output,
            prompt=prompt,
            texts=texts,
            tone_name=tone_name,
        )

    @step
    async def validate(
        self, ctx: Context, ev: ExtractionDone
    ) -> StopEvent | ValidationErrorEvent:
        """Validate extracted output against Pydantic schema."""
        raw_output = ev.output

        try:
            parsed = self.output_parser.parse(raw_output)
            return StopEvent(result={"success": parsed})

        except (ValidationError, ValueError, Exception) as e:
            error_msg = self._format_error(e, raw_output)
            await ctx.set("last_error", error_msg)

            retries = await ctx.get("retries", default=0)
            logger.error(
                f"LLM parse error (attempt {retries}/{self.max_retries}): "
                f"{type(e).__name__}: {e}\nRaw response: {raw_output[:500]}"
            )

            return ValidationErrorEvent(
                error=error_msg,
                wrong_output=raw_output,
                prompt=ev.prompt,
                texts=ev.texts,
                tone_name=ev.tone_name,
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
        """Get structured output from LLM with validation retry via Workflow."""
        workflow = StructuredOutputWorkflow(
            output_cls=output_cls,
            max_retries=self.settings_obj.LLM_PARSE_RETRY_ATTEMPTS,
            timeout=120,
        )

        result = await workflow.run(
            prompt=prompt,
            texts=texts,
            tone_name=tone_name,
        )

        if "error" in result:
            error_msg = result["error"] or "Max retries exceeded"
            raise ValueError(f"Failed to parse {output_cls.__name__}: {error_msg}")

        return result["success"]
