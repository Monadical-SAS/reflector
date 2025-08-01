from textwrap import dedent

from pydantic import BaseModel, Field

from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.types import TitleSummary, Transcript
from reflector.settings import settings

TOPIC_PROMPT = dedent(
    """
    Analyze the following transcript segment and extract the main topic being discussed.
    Focus on the substantive content and ignore small talk or administrative chatter.

    Create a title that:
    - Captures the specific subject matter being discussed
    - Is descriptive and self-explanatory
    - Uses professional language
    - Is specific rather than generic

    For the summary:
    - Summarize the key points in maximum two sentences
    - Focus on what was discussed, decided, or accomplished
    - Be concise but informative

    <transcript>
    {text}
    <transcript>
    """
).strip()


class TopicResponse(BaseModel):
    """Structured response for topic detection"""

    title: str = Field(description="A descriptive title for the topic being discussed")
    summary: str = Field(description="A concise 1-2 sentence summary of the discussion")


class TranscriptTopicDetectorProcessor(Processor):
    """
    Detect topic and summary from the transcript using LlamaIndex
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = TitleSummary

    def __init__(
        self, min_transcript_length: int = int(settings.MIN_TRANSCRIPT_LENGTH), **kwargs
    ):
        super().__init__(**kwargs)
        self.transcript = None
        self.min_transcript_length = min_transcript_length
        self.llm = LLM(settings=settings, temperature=0.9, max_tokens=500)

    async def _push(self, data: Transcript):
        if self.transcript is None:
            self.transcript = data
        else:
            self.transcript.merge(data)
        text_length = len(self.transcript.text)
        required_length = self.min_transcript_length
        if text_length <= required_length:
            self.logger.info(f"Topic detector {text_length}/{required_length}")
            return
        await self.flush()

    async def get_topic(self, text: str) -> TopicResponse:
        """
        Generate a topic and description for a transcription excerpt using LLM
        """
        prompt = TOPIC_PROMPT.format(text=text)

        # Always use structured response since we're assuming no function calling
        response = await self.llm.get_structured_response(
            prompt, [text], TopicResponse, tone_name="Topic analyzer"
        )
        return response

    async def _flush(self):
        if not self.transcript:
            return

        text = self.transcript.text
        self.logger.info(f"Topic detector got {len(text)} length transcript")

        topic_result = await self.get_topic(text=text)

        # Clean and format the title
        title = self._clean_title(topic_result.title)

        summary = TitleSummary(
            title=title,
            summary=topic_result.summary,
            timestamp=self.transcript.timestamp,
            duration=self.transcript.duration,
            transcript=self.transcript,
        )
        self.transcript = None
        await self.emit(summary)

    def _clean_title(self, title: str) -> str:
        """Clean and format the title"""
        # Remove quotes if present
        title = title.strip("\"'")

        # Limit length to reasonable size for topics
        if len(title) > 80:
            title = title[:77] + "..."

        # Ensure proper capitalization
        words = title.split()
        if words:
            # Capitalize first word and important words
            words = [
                word.capitalize() if i == 0 or len(word) > 3 else word.lower()
                for i, word in enumerate(words)
            ]
            title = " ".join(words)

        return title
