from reflector.llm.openai_llm import OpenAILLM
from reflector.processors.base import Processor
from reflector.processors.summary.summary_builder import SummaryBuilder
from reflector.processors.types import FinalLongSummary, FinalShortSummary, TitleSummary


class TranscriptFinalSummaryProcessor(Processor):
    """
    Get the final (long and short) summary
    """

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = FinalLongSummary

    def __init__(self, transcript=None, **kwargs):
        super().__init__(**kwargs)
        self.transcript = transcript
        self.chunks: list[TitleSummary] = []
        # Use OpenAILLM with SUMMARY_ prefix configuration
        self.llm = OpenAILLM(config_prefix="SUMMARY")
        self.builder = None

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_summary_builder(self, text) -> SummaryBuilder:
        builder = SummaryBuilder(self.llm, logger=self.logger)
        builder.set_transcript(text)
        await builder.identify_participants()
        await builder.generate_summary()
        return builder

    async def get_long_summary(self, text) -> str:
        if not self.builder:
            self.builder = await self.get_summary_builder(text)
        return self.builder.as_markdown()

    async def get_short_summary(self, text) -> str | None:
        if not self.builder:
            self.builder = await self.get_summary_builder(text)
        return self.builder.recap

    async def _flush(self):
        if not self.chunks:
            self.logger.warning("No summary to output")
            return

        # build the speakermap from the transcript
        speakermap = {}
        if self.transcript:
            speakermap = {
                participant["speaker"]: participant["name"]
                for participant in self.transcript.participants
            }

        # build the transcript as a single string
        # XXX: unsure if the participants name as replaced directly in speaker ?
        text_transcript = []
        for topic in self.chunks:
            for segment in topic.transcript.as_segments():
                name = speakermap.get(segment.speaker, f"Speaker {segment.speaker}")
                text_transcript.append(f"{name}: {segment.text}")

        text_transcript = "\n".join(text_transcript)

        last_chunk = self.chunks[-1]
        duration = last_chunk.timestamp + last_chunk.duration

        long_summary = await self.get_long_summary(text_transcript)
        short_summary = await self.get_short_summary(text_transcript)

        final_long_summary = FinalLongSummary(
            long_summary=long_summary,
            duration=duration,
        )

        if short_summary:
            final_short_summary = FinalShortSummary(
                short_summary=short_summary,
                duration=duration,
            )
            await self.emit(final_short_summary, name="short_summary")

        await self.emit(final_long_summary)
