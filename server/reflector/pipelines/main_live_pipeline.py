"""
Main reflector pipeline for live streaming
==========================================

This is the default pipeline used in the API.

It is decoupled to:
- PipelineMainLive: have limited processing during live
- PipelineMainPost: do heavy lifting after the live

It is directly linked to our data model.
"""

from pathlib import Path

from reflector.db.transcripts import (
    Transcript,
    TranscriptFinalLongSummary,
    TranscriptFinalShortSummary,
    TranscriptFinalTitle,
    TranscriptText,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.pipelines.runner import PipelineRunner
from reflector.processors import (
    AudioChunkerProcessor,
    AudioFileWriterProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    BroadcastProcessor,
    Pipeline,
    TranscriptFinalLongSummaryProcessor,
    TranscriptFinalShortSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptTranslatorProcessor,
)
from reflector.tasks.worker import celery
from reflector.ws_manager import WebsocketManager, get_ws_manager


def broadcast_to_socket(func):
    """
    Decorator to broadcast transcript event to websockets
    concerning this transcript
    """

    async def wrapper(self, *args, **kwargs):
        resp = await func(self, *args, **kwargs)
        if resp is None:
            return
        await self.ws_manager.send_json(
            room_id=self.ws_room_id,
            message=resp.model_dump(mode="json"),
        )

    return wrapper


class PipelineMainBase(PipelineRunner):
    transcript_id: str
    ws_room_id: str | None = None
    ws_manager: WebsocketManager | None = None

    def prepare(self):
        # prepare websocket
        self.ws_room_id = f"ts:{self.transcript_id}"
        self.ws_manager = get_ws_manager()

    async def get_transcript(self) -> Transcript:
        # fetch the transcript
        result = await transcripts_controller.get_by_id(
            transcript_id=self.transcript_id
        )
        if not result:
            raise Exception("Transcript not found")
        return result


class PipelineMainLive(PipelineMainBase):
    audio_filename: Path | None = None
    source_language: str = "en"
    target_language: str = "en"

    @broadcast_to_socket
    async def on_transcript(self, data):
        async with transcripts_controller.transaction():
            transcript = await self.get_transcript()
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="TRANSCRIPT",
                data=TranscriptText(text=data.text, translation=data.translation),
            )

    @broadcast_to_socket
    async def on_topic(self, data):
        topic = TranscriptTopic(
            title=data.title,
            summary=data.summary,
            timestamp=data.timestamp,
            text=data.transcript.text,
            words=data.transcript.words,
        )
        async with transcripts_controller.transaction():
            transcript = await self.get_transcript()
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="TOPIC",
                data=topic,
            )

    async def create(self) -> Pipeline:
        # create a context for the whole rtc transaction
        # add a customised logger to the context
        self.prepare()
        transcript = await self.get_transcript()

        processors = [
            AudioFileWriterProcessor(path=transcript.audio_mp3_filename),
            AudioChunkerProcessor(),
            AudioMergeProcessor(),
            AudioTranscriptAutoProcessor.as_threaded(),
            TranscriptLinerProcessor(),
            TranscriptTranslatorProcessor.as_threaded(callback=self.on_transcript),
            TranscriptTopicDetectorProcessor.as_threaded(callback=self.on_topic),
        ]
        pipeline = Pipeline(*processors)
        pipeline.options = self
        pipeline.set_pref("audio:source_language", transcript.source_language)
        pipeline.set_pref("audio:target_language", transcript.target_language)

        # when the pipeline ends, connect to the post pipeline
        async def on_ended():
            task_pipeline_main_post.delay(transcript_id=self.transcript_id)

        pipeline.on_ended = self

        return pipeline


class PipelineMainPost(PipelineMainBase):
    """
    Implement the rest of the main pipeline, triggered after PipelineMainLive ended.
    """

    @broadcast_to_socket
    async def on_final_title(self, data):
        final_title = TranscriptFinalTitle(title=data.title)
        async with transcripts_controller.transaction():
            transcript = await self.get_transcript()
            if not transcript.title:
                transcripts_controller.update(
                    self.transcript,
                    {
                        "title": final_title.title,
                    },
                )
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="FINAL_TITLE",
                data=final_title,
            )

    @broadcast_to_socket
    async def on_final_long_summary(self, data):
        final_long_summary = TranscriptFinalLongSummary(long_summary=data.long_summary)
        async with transcripts_controller.transaction():
            transcript = await self.get_transcript()
            await transcripts_controller.update(
                transcript,
                {
                    "long_summary": final_long_summary.long_summary,
                },
            )
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="FINAL_LONG_SUMMARY",
                data=final_long_summary,
            )

    @broadcast_to_socket
    async def on_final_short_summary(self, data):
        final_short_summary = TranscriptFinalShortSummary(
            short_summary=data.short_summary
        )
        async with transcripts_controller.transaction():
            transcript = await self.get_transcript()
            await transcripts_controller.update(
                transcript,
                {
                    "short_summary": final_short_summary.short_summary,
                },
            )
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="FINAL_SHORT_SUMMARY",
                data=final_short_summary,
            )

    async def create(self) -> Pipeline:
        # create a context for the whole rtc transaction
        # add a customised logger to the context
        self.prepare()
        processors = [
            # add diarization
            BroadcastProcessor(
                processors=[
                    TranscriptFinalTitleProcessor.as_threaded(
                        callback=self.on_final_title
                    ),
                    TranscriptFinalLongSummaryProcessor.as_threaded(
                        callback=self.on_final_long_summary
                    ),
                    TranscriptFinalShortSummaryProcessor.as_threaded(
                        callback=self.on_final_short_summary
                    ),
                ]
            ),
        ]
        pipeline = Pipeline(*processors)
        pipeline.options = self

        return pipeline


@celery.task
def task_pipeline_main_post(transcript_id: str):
    pass
