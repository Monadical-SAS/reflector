from reflector.llm import LLM
from reflector.processors.base import Processor
from reflector.processors.summary.summary_builder import SummaryBuilder
from reflector.processors.types import (
    FinalActionItems,
    FinalLongSummary,
    FinalShortSummary,
    TitleSummary,
)
from reflector.settings import settings


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
        self.llm = LLM(settings=settings)
        self.builder = None

    async def _push(self, data: TitleSummary):
        self.chunks.append(data)

    async def get_summary_builder(self, text) -> SummaryBuilder:
        builder = SummaryBuilder(self.llm, logger=self.logger)
        builder.set_transcript(text)

        if self.transcript and self.transcript.participants:
            participant_names = [p.name for p in self.transcript.participants if p.name]
            if participant_names:
                self.logger.info(
                    f"Using {len(participant_names)} known participants from transcript"
                )
                participant_name_to_id = {
                    p.name: p.id
                    for p in self.transcript.participants
                    if p.name and p.id
                }
                builder.set_known_participants(
                    participant_names, participant_name_to_id=participant_name_to_id
                )
            else:
                self.logger.info(
                    "Participants field exists but is empty, identifying participants"
                )
                await builder.identify_participants()
        else:
            self.logger.info("No participants stored, identifying participants")
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

        speakermap = {}
        if self.transcript:
            speakermap = {
                p.speaker: p.name
                for p in (self.transcript.participants or [])
                if p.speaker is not None and p.name
            }
            self.logger.info(
                f"Built speaker map with {len(speakermap)} participants",
                speakermap=speakermap,
            )

        text_transcript = []
        unique_speakers = set()
        for topic in self.chunks:
            for segment in topic.transcript.as_segments():
                name = speakermap.get(segment.speaker, f"Speaker {segment.speaker}")
                unique_speakers.add((segment.speaker, name))
                text_transcript.append(f"{name}: {segment.text}")

        self.logger.info(
            f"Built transcript with {len(unique_speakers)} unique speakers",
            speakers=list(unique_speakers),
        )

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

        if self.builder and self.builder.action_items:
            action_items = self.builder.action_items.model_dump()
            final_action_items = FinalActionItems(action_items=action_items)
            await self.emit(final_action_items, name="action_items")

        await self.emit(final_long_summary)
