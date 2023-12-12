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
import functools
from contextlib import asynccontextmanager

from celery import chord, group, shared_task
from pydantic import BaseModel
from reflector.db.transcripts import (
    Transcript,
    TranscriptDuration,
    TranscriptFinalLongSummary,
    TranscriptFinalShortSummary,
    TranscriptFinalTitle,
    TranscriptText,
    TranscriptTopic,
    TranscriptWaveform,
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
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.processors.types import AudioDiarizationInput
from reflector.processors.types import (
    TitleSummaryWithId as TitleSummaryWithIdProcessorType,
)
from reflector.processors.types import Transcript as TranscriptProcessorType
from reflector.settings import settings
from reflector.ws_manager import WebsocketManager, get_ws_manager
from structlog import BoundLogger as Logger


def asynctask(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        coro = f(*args, **kwargs)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            return loop.run_until_complete(coro)
        return asyncio.run(coro)

    return wrapper


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


def get_transcript(func):
    """
    Decorator to fetch the transcript from the database from the first argument
    """

    async def wrapper(**kwargs):
        transcript_id = kwargs.pop("transcript_id")
        transcript = await transcripts_controller.get_by_id(transcript_id=transcript_id)
        if not transcript:
            raise Exception("Transcript {transcript_id} not found")
        tlogger = logger.bind(transcript_id=transcript.id)
        try:
            return await func(transcript=transcript, logger=tlogger, **kwargs)
        except Exception as exc:
            tlogger.error("Pipeline error", exc_info=exc)
            raise

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

    def get_transcript_topics(self, transcript: Transcript) -> list[TranscriptTopic]:
        return [
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
        elif isinstance(self, PipelineMainFinalSummaries):
            status_mapping = {
                "push": "processing",
                "flush": "processing",
                "error": "error",
                "ended": "ended",
            }
        else:
            # intermediate pipeline don't update status
            return

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

    @broadcast_to_sockets
    async def on_duration(self, data):
        async with self.transaction():
            duration = TranscriptDuration(duration=data)

            transcript = await self.get_transcript()
            await transcripts_controller.update(
                transcript,
                {
                    "duration": duration.duration,
                },
            )
            return await transcripts_controller.append_event(
                transcript=transcript, event="DURATION", data=duration
            )

    @broadcast_to_sockets
    async def on_waveform(self, data):
        async with self.transaction():
            waveform = TranscriptWaveform(waveform=data)

            transcript = await self.get_transcript()

            return await transcripts_controller.append_event(
                transcript=transcript, event="WAVEFORM", data=waveform
            )


class PipelineMainLive(PipelineMainBase):
    """
    Main pipeline for live streaming, attach to RTC connection
    Any long post process should be done in the post pipeline
    """

    async def create(self) -> Pipeline:
        # create a context for the whole rtc transaction
        # add a customised logger to the context
        self.prepare()
        transcript = await self.get_transcript()

        processors = [
            AudioFileWriterProcessor(
                path=transcript.audio_wav_filename,
                on_duration=self.on_duration,
            ),
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
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info("Pipeline main live created")

        return pipeline

    async def on_ended(self):
        # when the pipeline ends, connect to the post pipeline
        logger.info("Pipeline main live ended", transcript_id=self.transcript_id)
        logger.info("Scheduling pipeline main post", transcript_id=self.transcript_id)
        pipeline_post(transcript_id=self.transcript_id)


class PipelineMainDiarization(PipelineMainBase):
    """
    Diarize the audio and update topics
    """

    async def create(self) -> Pipeline:
        # create a context for the whole rtc transaction
        # add a customised logger to the context
        self.prepare()
        pipeline = Pipeline(
            AudioDiarizationAutoProcessor(callback=self.on_topic),
        )
        pipeline.options = self

        # now let's start the pipeline by pushing information to the
        # first processor diarization processor
        # XXX translation is lost when converting our data model to the processor model
        transcript = await self.get_transcript()

        # diarization works only if the file is uploaded to an external storage
        if transcript.audio_location == "local":
            pipeline.logger.info("Audio is local, skipping diarization")
            return

        topics = self.get_transcript_topics(transcript)
        audio_url = await transcript.get_audio_url()
        audio_diarization_input = AudioDiarizationInput(
            audio_url=audio_url,
            topics=topics,
        )

        # as tempting to use pipeline.push, prefer to use the runner
        # to let the start just do one job.
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info("Diarization pipeline created")
        self.push(audio_diarization_input)
        self.flush()

        return pipeline


class PipelineMainFromTopics(PipelineMainBase):
    """
    Pseudo class for generating a pipeline from topics
    """

    def get_processors(self) -> list:
        raise NotImplementedError

    async def create(self) -> Pipeline:
        self.prepare()

        # get transcript
        self._transcript = transcript = await self.get_transcript()

        # create pipeline
        processors = self.get_processors()
        pipeline = Pipeline(*processors)
        pipeline.options = self
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info(f"{self.__class__.__name__} pipeline created")

        # push topics
        topics = self.get_transcript_topics(transcript)
        for topic in topics:
            self.push(topic)

        self.flush()

        return pipeline


class PipelineMainTitleAndShortSummary(PipelineMainFromTopics):
    """
    Generate title from the topics
    """

    def get_processors(self) -> list:
        return [
            BroadcastProcessor(
                processors=[
                    TranscriptFinalTitleProcessor.as_threaded(callback=self.on_title),
                    TranscriptFinalShortSummaryProcessor.as_threaded(
                        callback=self.on_short_summary
                    ),
                ]
            )
        ]


class PipelineMainFinalSummaries(PipelineMainFromTopics):
    """
    Generate summaries from the topics
    """

    def get_processors(self) -> list:
        return [
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


class PipelineMainWaveform(PipelineMainFromTopics):
    """
    Generate waveform
    """

    def get_processors(self) -> list:
        return [
            AudioWaveformProcessor.as_threaded(
                audio_path=self._transcript.audio_wav_filename,
                waveform_path=self._transcript.audio_waveform_filename,
                on_waveform=self.on_waveform,
            ),
        ]


@get_transcript
async def pipeline_waveform(transcript: Transcript, logger: Logger):
    logger.info("Starting waveform")
    runner = PipelineMainWaveform(transcript_id=transcript.id)
    await runner.run()
    logger.info("Waveform done")


@get_transcript
async def pipeline_convert_to_mp3(transcript: Transcript, logger: Logger):
    logger.info("Starting convert to mp3")

    # If the audio wav is not available, just skip
    wav_filename = transcript.audio_wav_filename
    if not wav_filename.exists():
        logger.warning("Wav file not found, may be already converted")
        return

    # Convert to mp3
    mp3_filename = transcript.audio_mp3_filename

    import av

    with av.open(wav_filename.as_posix()) as in_container:
        in_stream = in_container.streams.audio[0]
        with av.open(mp3_filename.as_posix(), "w") as out_container:
            out_stream = out_container.add_stream("mp3")
            for frame in in_container.decode(in_stream):
                for packet in out_stream.encode(frame):
                    out_container.mux(packet)

    # Delete the wav file
    transcript.audio_wav_filename.unlink(missing_ok=True)

    logger.info("Convert to mp3 done")


@get_transcript
async def pipeline_upload_mp3(transcript: Transcript, logger: Logger):
    if not settings.TRANSCRIPT_STORAGE_BACKEND:
        logger.info("No storage backend configured, skipping mp3 upload")
        return

    logger.info("Starting upload mp3")

    # If the audio mp3 is not available, just skip
    mp3_filename = transcript.audio_mp3_filename
    if not mp3_filename.exists():
        logger.warning("Mp3 file not found, may be already uploaded")
        return

    # Upload to external storage and delete the file
    await transcripts_controller.move_mp3_to_storage(transcript)

    logger.info("Upload mp3 done")


@get_transcript
async def pipeline_diarization(transcript: Transcript, logger: Logger):
    logger.info("Starting diarization")
    runner = PipelineMainDiarization(transcript_id=transcript.id)
    await runner.run()
    logger.info("Diarization done")


@get_transcript
async def pipeline_title_and_short_summary(transcript: Transcript, logger: Logger):
    logger.info("Starting title and short summary")
    runner = PipelineMainTitleAndShortSummary(transcript_id=transcript.id)
    await runner.run()
    logger.info("Title and short summary done")


@get_transcript
async def pipeline_summaries(transcript: Transcript, logger: Logger):
    logger.info("Starting summaries")
    runner = PipelineMainFinalSummaries(transcript_id=transcript.id)
    await runner.run()
    logger.info("Summaries done")


# ===================================================================
# Celery tasks that can be called from the API
# ===================================================================


@shared_task
@asynctask
async def task_pipeline_waveform(*, transcript_id: str):
    await pipeline_waveform(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_convert_to_mp3(*, transcript_id: str):
    await pipeline_convert_to_mp3(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_upload_mp3(*, transcript_id: str):
    await pipeline_upload_mp3(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_diarization(*, transcript_id: str):
    await pipeline_diarization(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_title_and_short_summary(*, transcript_id: str):
    await pipeline_title_and_short_summary(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_final_summaries(*, transcript_id: str):
    await pipeline_summaries(transcript_id=transcript_id)


def pipeline_post(*, transcript_id: str):
    """
    Run the post pipeline
    """
    chain_mp3_and_diarize = (
        task_pipeline_waveform.si(transcript_id=transcript_id)
        | task_pipeline_convert_to_mp3.si(transcript_id=transcript_id)
        | task_pipeline_upload_mp3.si(transcript_id=transcript_id)
        | task_pipeline_diarization.si(transcript_id=transcript_id)
    )
    chain_title_preview = task_pipeline_title_and_short_summary.si(
        transcript_id=transcript_id
    )
    chain_final_summaries = task_pipeline_final_summaries.si(
        transcript_id=transcript_id
    )

    chain = chord(
        group(chain_mp3_and_diarize, chain_title_preview),
        chain_final_summaries,
    )
    chain.delay()


@get_transcript
async def pipeline_upload(transcript: Transcript, logger: Logger):
    import av

    try:
        # open audio
        upload_filename = next(transcript.data_path.glob("upload.*"))
        container = av.open(upload_filename.as_posix())

        # create pipeline
        pipeline = PipelineMainLive(transcript_id=transcript.id)
        pipeline.start()

        # push audio to pipeline
        try:
            logger.info("Start pushing audio into the pipeline")
            for frame in container.decode(audio=0):
                pipeline.push(frame)
        finally:
            logger.info("Flushing the pipeline")
            pipeline.flush()

        logger.info("Waiting for the pipeline to end")
        await pipeline.join()

    except Exception as exc:
        logger.error("Pipeline error", exc_info=exc)
        await transcripts_controller.update(
            transcript,
            {
                "status": "error",
            },
        )
        raise

    logger.info("Pipeline ended")


@shared_task
@asynctask
async def task_pipeline_upload(*, transcript_id: str):
    return await pipeline_upload(transcript_id=transcript_id)
