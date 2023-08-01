from reflector.processors.base import Processor
from reflector.processors.types import Transcript, TitleSummary
from reflector.llm import LLM


class TranscriptTopicDetectorProcessor(Processor):
    """
    Detect topic and summary from the transcript
    """

    INPUT_TYPE = Transcript
    OUTPUT_TYPE = TitleSummary

    PROMPT = """
        ### Human:
        Create a JSON object as response.The JSON object must have 2 fields:
        i) title and ii) summary.For the title field,generate a short title
        for the given text. For the summary field, summarize the given text
        in three sentences.

        {input_text}

        ### Assistant:

    """

    def __init__(self, min_transcript_length=100, **kwargs):
        super().__init__(**kwargs)
        self.transcript = None
        self.min_transcript_length = min_transcript_length
        self.llm = LLM.instance()

    async def _push(self, data: Transcript):
        if self.transcript is None:
            self.transcript = data
        else:
            self.transcript.merge(data)
        if len(self.transcript.text) < self.min_transcript_length:
            return
        await self.flush()

    async def _flush(self):
        if not self.transcript:
            return
        prompt = self.PROMPT.format(input_text=self.transcript.text)
        result = await self.llm.generate(prompt=prompt)
        summary = TitleSummary(
            title=result["title"],
            summary=result["summary"],
            timestamp=self.transcript.timestamp,
            duration=self.transcript.duration,
            transcript=self.transcript,
        )
        self.transcript = None
        await self.emit(summary)
