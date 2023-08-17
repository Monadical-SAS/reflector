from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.types import TitleSummary, Transcript
from reflector.utils.retry import retry


class TranscriptTopicDetectorProcessor(Processor):
    """
    Detect topic and summary from the transcript
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = TitleSummary

    PROMPT = """
        ### Human:
        Create a JSON object as response.The JSON object must have 2 fields:
        i) title and ii) summary.

        For the title field, generate a short title for the given text.
        For the summary field, summarize the given text in a maximum of
        three sentences.

        {input_text}

        ### Assistant:

    """

    def __init__(self, min_transcript_length=750, **kwargs):
        super().__init__(**kwargs)
        self.transcript = None
        self.min_transcript_length = min_transcript_length
        self.llm = LLM.get_instance()
        self.topic_detector_schema = {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "summary": {"type": "string"},
            },
        }

    async def _warmup(self):
        await self.llm.warmup(logger=self.logger)

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

    async def _flush(self):
        if not self.transcript:
            return
        text = self.transcript.text
        self.logger.info(f"Topic detector got {len(text)} length transcript")
        prompt = self.PROMPT.format(input_text=text)
        result = await retry(self.llm.generate)(
            prompt=prompt, schema=self.topic_detector_schema, logger=self.logger
        )
        summary = TitleSummary(
            title=result["title"],
            summary=result["summary"],
            timestamp=self.transcript.timestamp,
            duration=self.transcript.duration,
            transcript=self.transcript,
        )
        self.transcript = None
        await self.emit(summary)
