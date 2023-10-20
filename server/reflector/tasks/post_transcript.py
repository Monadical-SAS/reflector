from reflector.logger import logger
from reflector.processors import (
    Pipeline,
    Processor,
    TranscriptFinalLongSummaryProcessor,
    TranscriptFinalShortSummaryProcessor,
    TranscriptFinalTitleProcessor,
)
from reflector.processors.base import BroadcastProcessor
from reflector.processors.types import (
    FinalLongSummary,
    FinalShortSummary,
    FinalTitle,
    TitleSummary,
)
from reflector.processors.types import Transcript as ProcessorTranscript
from reflector.tasks.worker import celery
from reflector.views.rtc_offer import PipelineEvent, TranscriptionContext
from reflector.views.transcripts import Transcript, transcripts_controller


class TranscriptAudioDiarizationProcessor(Processor):
    INPUT_TYPE = Transcript
    OUTPUT_TYPE = TitleSummary

    async def _push(self, data: Transcript):
        # Gather diarization data
        diarization = [
            {"start": 0.0, "stop": 4.9, "speaker": 2},
            {"start": 5.6, "stop": 6.7, "speaker": 2},
            {"start": 7.3, "stop": 8.9, "speaker": 2},
            {"start": 7.3, "stop": 7.9, "speaker": 0},
            {"start": 9.4, "stop": 11.2, "speaker": 2},
            {"start": 9.7, "stop": 10.0, "speaker": 0},
            {"start": 10.0, "stop": 10.1, "speaker": 0},
            {"start": 11.7, "stop": 16.1, "speaker": 2},
            {"start": 11.8, "stop": 12.1, "speaker": 1},
            {"start": 16.4, "stop": 21.0, "speaker": 2},
            {"start": 21.1, "stop": 22.6, "speaker": 2},
            {"start": 24.7, "stop": 31.9, "speaker": 2},
            {"start": 32.0, "stop": 32.8, "speaker": 1},
            {"start": 33.4, "stop": 37.8, "speaker": 2},
            {"start": 37.9, "stop": 40.3, "speaker": 0},
            {"start": 39.2, "stop": 40.4, "speaker": 2},
            {"start": 40.7, "stop": 41.4, "speaker": 0},
            {"start": 41.6, "stop": 45.7, "speaker": 2},
            {"start": 46.4, "stop": 53.1, "speaker": 2},
            {"start": 53.6, "stop": 56.5, "speaker": 2},
            {"start": 54.9, "stop": 75.4, "speaker": 1},
            {"start": 57.3, "stop": 58.0, "speaker": 2},
            {"start": 65.7, "stop": 66.0, "speaker": 2},
            {"start": 75.8, "stop": 78.8, "speaker": 1},
            {"start": 79.0, "stop": 82.6, "speaker": 1},
            {"start": 83.2, "stop": 83.3, "speaker": 1},
            {"start": 84.5, "stop": 94.3, "speaker": 1},
            {"start": 95.1, "stop": 100.7, "speaker": 1},
            {"start": 100.7, "stop": 102.0, "speaker": 0},
            {"start": 100.7, "stop": 101.8, "speaker": 1},
            {"start": 102.0, "stop": 103.0, "speaker": 1},
            {"start": 103.0, "stop": 103.7, "speaker": 0},
            {"start": 103.7, "stop": 103.8, "speaker": 1},
            {"start": 103.8, "stop": 113.9, "speaker": 0},
            {"start": 114.7, "stop": 117.0, "speaker": 0},
            {"start": 117.0, "stop": 117.4, "speaker": 1},
        ]

        # now reapply speaker to topics (if any)
        # topics is a list[BaseModel] with an attribute words
        # words is a list[BaseModel] with text, start and speaker attribute

        # mutate in place
        for topic in data.topics:
            for word in topic.words:
                for d in diarization:
                    if d["start"] <= word.start <= d["stop"]:
                        word.speaker = d["speaker"]

        topics = data.topics[:]

        await transcripts_controller.update(
            data,
            {
                "topics": [topic.model_dump(mode="json") for topic in data.topics],
            },
        )

        # emit them
        for topic in topics:
            transcript = ProcessorTranscript(words=topic.words)
            await self.emit(
                TitleSummary(
                    title=topic.title,
                    summary=topic.summary,
                    timestamp=topic.timestamp,
                    duration=0,
                    transcript=transcript,
                )
            )


@celery.task(name="post_transcript")
async def post_transcript_pipeline(transcript_id: str):
    # get transcript
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        logger.error("Transcript not found", transcript_id=transcript_id)
        return

    ctx = TranscriptionContext(logger=logger.bind(transcript_id=transcript_id))
    event_callback = None
    event_callback_args = None

    async def on_final_short_summary(summary: FinalShortSummary):
        ctx.logger.info("FinalShortSummary", final_short_summary=summary)

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.FINAL_SHORT_SUMMARY,
                args=event_callback_args,
                data=summary,
            )

    async def on_final_long_summary(summary: FinalLongSummary):
        ctx.logger.info("FinalLongSummary", final_summary=summary)

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.FINAL_LONG_SUMMARY,
                args=event_callback_args,
                data=summary,
            )

    async def on_final_title(title: FinalTitle):
        ctx.logger.info("FinalTitle", final_title=title)

        # send to callback (eg. websocket)
        if event_callback:
            await event_callback(
                event=PipelineEvent.FINAL_TITLE,
                args=event_callback_args,
                data=title,
            )

    ctx.logger.info("Starting pipeline (diarization)")
    ctx.pipeline = Pipeline(
        TranscriptAudioDiarizationProcessor(),
        BroadcastProcessor(
            processors=[
                TranscriptFinalTitleProcessor.as_threaded(),
                TranscriptFinalLongSummaryProcessor.as_threaded(),
                TranscriptFinalShortSummaryProcessor.as_threaded(),
            ]
        ),
    )

    await ctx.pipeline.push(transcript)
    await ctx.pipeline.flush()


if __name__ == "__main__":
    import argparse
    import asyncio

    parser = argparse.ArgumentParser()
    parser.add_argument("transcript_id", type=str)
    args = parser.parse_args()

    asyncio.run(post_transcript_pipeline(args.transcript_id))
