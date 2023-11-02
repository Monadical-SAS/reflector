"""
Main reflector pipeline for live streaming
==========================================

This is the default pipeline used in the API.

It is decoupled to:
- PipelineMainLive: have limited processing during live
- PipelineMainPost: do heavy lifting after the live

It is directly linked to our data model.
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from celery import shared_task
from pydantic import BaseModel
from reflector.app import app
from reflector.db.transcripts import (
    Transcript,
    TranscriptFinalLongSummary,
    TranscriptFinalShortSummary,
    TranscriptFinalTitle,
    TranscriptText,
    TranscriptTopic,
    transcripts_controller,
)
from reflector.logger import logger
from reflector.pipelines.runner import PipelineRunner
from reflector.processors import (
    AudioChunkerProcessor,
    AudioDiarizationAutoProcessor,
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
from reflector.processors.types import AudioDiarizationInput
from reflector.processors.types import (
    TitleSummaryWithId as TitleSummaryWithIdProcessorType,
)
from reflector.processors.types import Transcript as TranscriptProcessorType
from reflector.settings import settings
from reflector.ws_manager import WebsocketManager, get_ws_manager


def broadcast_to_sockets(func):
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


class StrValue(BaseModel):
    value: str


class PipelineMainBase(PipelineRunner):
    transcript_id: str
    ws_room_id: str | None = None
    ws_manager: WebsocketManager | None = None

    def prepare(self):
        # prepare websocket
        self._lock = asyncio.Lock()
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

    @asynccontextmanager
    async def transaction(self):
        async with self._lock:
            async with transcripts_controller.transaction():
                yield

    @broadcast_to_sockets
    async def on_status(self, status):
        # if it's the first part, update the status of the transcript
        # but do not set the ended status yet.
        if isinstance(self, PipelineMainLive):
            status_mapping = {
                "started": "recording",
                "push": "recording",
                "flush": "processing",
                "error": "error",
            }
        elif isinstance(self, PipelineMainDiarization):
            status_mapping = {
                "push": "processing",
                "flush": "processing",
                "error": "error",
                "ended": "ended",
            }
        else:
            raise Exception(f"Runner {self.__class__} is missing status mapping")

        # mutate to model status
        status = status_mapping.get(status)
        if not status:
            return

        # when the status of the pipeline changes, update the transcript
        async with self.transaction():
            transcript = await self.get_transcript()
            if status == transcript.status:
                return
            resp = await transcripts_controller.append_event(
                transcript=transcript,
                event="STATUS",
                data=StrValue(value=status),
            )
            await transcripts_controller.update(
                transcript,
                {
                    "status": status,
                },
            )
            return resp

    @broadcast_to_sockets
    async def on_transcript(self, data):
        async with self.transaction():
            transcript = await self.get_transcript()
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="TRANSCRIPT",
                data=TranscriptText(text=data.text, translation=data.translation),
            )

    @broadcast_to_sockets
    async def on_topic(self, data):
        topic = TranscriptTopic(
            title=data.title,
            summary=data.summary,
            timestamp=data.timestamp,
            transcript=data.transcript.text,
            words=data.transcript.words,
        )
        if isinstance(data, TitleSummaryWithIdProcessorType):
            topic.id = data.id
        async with self.transaction():
            transcript = await self.get_transcript()
            await transcripts_controller.upsert_topic(transcript, topic)
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="TOPIC",
                data=topic,
            )

    @broadcast_to_sockets
    async def on_title(self, data):
        final_title = TranscriptFinalTitle(title=data.title)
        async with self.transaction():
            transcript = await self.get_transcript()
            if not transcript.title:
                await transcripts_controller.update(
                    transcript,
                    {
                        "title": final_title.title,
                    },
                )
            return await transcripts_controller.append_event(
                transcript=transcript,
                event="FINAL_TITLE",
                data=final_title,
            )

    @broadcast_to_sockets
    async def on_long_summary(self, data):
        final_long_summary = TranscriptFinalLongSummary(long_summary=data.long_summary)
        async with self.transaction():
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

    @broadcast_to_sockets
    async def on_short_summary(self, data):
        final_short_summary = TranscriptFinalShortSummary(
            short_summary=data.short_summary
        )
        async with self.transaction():
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


class PipelineMainLive(PipelineMainBase):
    audio_filename: Path | None = None
    source_language: str = "en"
    target_language: str = "en"

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
            BroadcastProcessor(
                processors=[
                    TranscriptFinalTitleProcessor.as_threaded(callback=self.on_title),
                ]
            ),
        ]
        pipeline = Pipeline(*processors)
        pipeline.options = self
        pipeline.set_pref("audio:source_language", transcript.source_language)
        pipeline.set_pref("audio:target_language", transcript.target_language)
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info(
            "Pipeline main live created",
            transcript_id=self.transcript_id,
        )

        return pipeline

    async def on_ended(self):
        # when the pipeline ends, connect to the post pipeline
        logger.info("Pipeline main live ended", transcript_id=self.transcript_id)
        logger.info("Scheduling pipeline main post", transcript_id=self.transcript_id)
        task_pipeline_main_post.delay(transcript_id=self.transcript_id)


class PipelineMainDiarization(PipelineMainBase):
    """
    Diarization is a long time process, so we do it in a separate pipeline
    When done, adjust the short and final summary
    """

    async def create(self) -> Pipeline:
        # create a context for the whole rtc transaction
        # add a customised logger to the context
        self.prepare()
        processors = [
            AudioDiarizationAutoProcessor(callback=self.on_topic),
            BroadcastProcessor(
                processors=[
                    TranscriptFinalLongSummaryProcessor.as_threaded(
                        callback=self.on_long_summary
                    ),
                    TranscriptFinalShortSummaryProcessor.as_threaded(
                        callback=self.on_short_summary
                    ),
                ]
            ),
        ]
        pipeline = Pipeline(*processors)
        pipeline.options = self

        # now let's start the pipeline by pushing information to the
        # first processor diarization processor
        # XXX translation is lost when converting our data model to the processor model
        transcript = await self.get_transcript()
        topics = [
            TitleSummaryWithIdProcessorType(
                id=topic.id,
                title=topic.title,
                summary=topic.summary,
                timestamp=topic.timestamp,
                duration=topic.duration,
                transcript=TranscriptProcessorType(words=topic.words),
            )
            for topic in transcript.topics
        ]

        # we need to create an url to be used for diarization
        # we can't use the audio_mp3_filename because it's not accessible
        # from the diarization processor
        from reflector.views.transcripts import create_access_token

        token = create_access_token(
            {"sub": transcript.user_id},
            expires_delta=timedelta(minutes=15),
        )
        path = app.url_path_for(
            "transcript_get_audio_mp3",
            transcript_id=transcript.id,
        )
        url = f"{settings.BASE_URL}{path}?token={token}"
        audio_diarization_input = AudioDiarizationInput(
            audio_url=url,
            topics=topics,
        )

        # as tempting to use pipeline.push, prefer to use the runner
        # to let the start just do one job.
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info(
            "Pipeline main post created", transcript_id=self.transcript_id
        )
        self.push(audio_diarization_input)
        self.flush()

        return pipeline


@shared_task
def task_pipeline_main_post(transcript_id: str):
    logger.info(
        "Starting main post pipeline",
        transcript_id=transcript_id,
    )
    runner = PipelineMainDiarization(transcript_id=transcript_id)
    runner.start_sync()
