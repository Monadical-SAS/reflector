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
from typing import Generic

import av
import boto3
from celery import chord, current_task, group, shared_task
from pydantic import BaseModel
from structlog import BoundLogger as Logger

from reflector.db import get_database
from reflector.db.meetings import meeting_consent_controller, meetings_controller
from reflector.db.recordings import recordings_controller
from reflector.db.rooms import rooms_controller
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
from reflector.pipelines.runner import PipelineMessage, PipelineRunner
from reflector.processors import (
    AudioChunkerAutoProcessor,
    AudioDiarizationAutoProcessor,
    AudioDownscaleProcessor,
    AudioFileWriterProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    Pipeline,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptTranslatorAutoProcessor,
)
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.processors.types import AudioDiarizationInput
from reflector.processors.types import (
    TitleSummaryWithId as TitleSummaryWithIdProcessorType,
)
from reflector.processors.types import Transcript as TranscriptProcessorType
from reflector.settings import settings
from reflector.storage import get_transcripts_storage
from reflector.ws_manager import WebsocketManager, get_ws_manager
from reflector.zulip import (
    get_zulip_message,
    send_message_to_zulip,
    update_zulip_message,
)


def asynctask(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        async def run_with_db():
            database = get_database()
            await database.connect()
            try:
                return await f(*args, **kwargs)
            finally:
                await database.disconnect()

        coro = run_with_db()
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

    @functools.wraps(func)
    async def wrapper(**kwargs):
        transcript_id = kwargs.pop("transcript_id")
        transcript = await transcripts_controller.get_by_id(transcript_id=transcript_id)
        if not transcript:
            raise Exception("Transcript {transcript_id} not found")

        # Enhanced logger with Celery task context
        tlogger = logger.bind(transcript_id=transcript.id)
        if current_task:
            tlogger = tlogger.bind(
                task_id=current_task.request.id,
                task_name=current_task.name,
                worker_hostname=current_task.request.hostname,
                task_retries=current_task.request.retries,
                transcript_id=transcript_id,
            )

        try:
            result = await func(transcript=transcript, logger=tlogger, **kwargs)
            return result
        except Exception as exc:
            tlogger.error("Pipeline error", function_name=func.__name__, exc_info=exc)
            raise

    return wrapper


class StrValue(BaseModel):
    value: str


class PipelineMainBase(PipelineRunner[PipelineMessage], Generic[PipelineMessage]):
    def __init__(self, transcript_id: str):
        super().__init__()
        self._lock = asyncio.Lock()
        self.transcript_id = transcript_id
        self.ws_room_id = f"ts:{self.transcript_id}"
        self._ws_manager = None

    @property
    def ws_manager(self) -> WebsocketManager:
        if self._ws_manager is None:
            self._ws_manager = get_ws_manager()
        return self._ws_manager

    async def get_transcript(self) -> Transcript:
        # fetch the transcript
        result = await transcripts_controller.get_by_id(
            transcript_id=self.transcript_id
        )
        if not result:
            raise Exception("Transcript not found")
        return result

    @staticmethod
    def wrap_transcript_topics(
        topics: list[TranscriptTopic],
    ) -> list[TitleSummaryWithIdProcessorType]:
        # transformation to a pipe-supported format
        return [
            TitleSummaryWithIdProcessorType(
                id=topic.id,
                title=topic.title,
                summary=topic.summary,
                timestamp=topic.timestamp,
                duration=topic.duration,
                transcript=TranscriptProcessorType(words=topic.words),
            )
            for topic in topics
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
        transcript = await self.get_transcript()

        processors = [
            AudioFileWriterProcessor(
                path=transcript.audio_wav_filename,
                on_duration=self.on_duration,
            ),
            AudioDownscaleProcessor(),
            AudioChunkerAutoProcessor(),
            AudioMergeProcessor(),
            AudioTranscriptAutoProcessor.as_threaded(),
            TranscriptLinerProcessor(),
            TranscriptTranslatorAutoProcessor.as_threaded(callback=self.on_transcript),
            TranscriptTopicDetectorProcessor.as_threaded(callback=self.on_topic),
        ]
        pipeline = Pipeline(*processors)
        pipeline.options = self
        pipeline.set_pref("audio:source_language", transcript.source_language)
        pipeline.set_pref("audio:target_language", transcript.target_language)
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info("Pipeline main live created")
        pipeline.describe()

        return pipeline

    async def on_ended(self):
        # when the pipeline ends, connect to the post pipeline
        logger.info("Pipeline main live ended", transcript_id=self.transcript_id)
        logger.info("Scheduling pipeline main post", transcript_id=self.transcript_id)
        pipeline_post(transcript_id=self.transcript_id)


class PipelineMainDiarization(PipelineMainBase[AudioDiarizationInput]):
    """
    Diarize the audio and update topics
    """

    async def create(self) -> Pipeline:
        # create a context for the whole rtc transaction
        # add a customised logger to the context
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

        audio_url = await transcript.get_audio_url()
        audio_diarization_input = AudioDiarizationInput(
            audio_url=audio_url,
            topics=self.wrap_transcript_topics(transcript.topics),
        )

        # as tempting to use pipeline.push, prefer to use the runner
        # to let the start just do one job.
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info("Diarization pipeline created")
        await self.push(audio_diarization_input)
        await self.flush()

        return pipeline


class PipelineMainFromTopics(PipelineMainBase[TitleSummaryWithIdProcessorType]):
    """
    Pseudo class for generating a pipeline from topics
    """

    def get_processors(self) -> list:
        raise NotImplementedError

    async def create(self) -> Pipeline:
        # get transcript
        self._transcript = transcript = await self.get_transcript()

        # create pipeline
        processors = self.get_processors()
        pipeline = Pipeline(*processors)
        pipeline.options = self
        pipeline.logger.bind(transcript_id=transcript.id)
        pipeline.logger.info(f"{self.__class__.__name__} pipeline created")

        # push topics
        topics = PipelineMainBase.wrap_transcript_topics(transcript.topics)
        for topic in topics:
            await self.push(topic)

        await self.flush()

        return pipeline


class PipelineMainTitle(PipelineMainFromTopics):
    """
    Generate title from the topics
    """

    def get_processors(self) -> list:
        return [
            TranscriptFinalTitleProcessor.as_threaded(callback=self.on_title),
        ]


class PipelineMainFinalSummaries(PipelineMainFromTopics):
    """
    Generate summaries from the topics
    """

    def get_processors(self) -> list:
        return [
            TranscriptFinalSummaryProcessor.as_threaded(
                transcript=self._transcript,
                callback=self.on_long_summary,
                on_short_summary=self.on_short_summary,
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
async def pipeline_remove_upload(transcript: Transcript, logger: Logger):
    # for future changes: note that there's also a consent process happens, beforehand and users may not consent with keeping files. currently, we delete regardless, so it's no need for that
    logger.info("Starting remove upload")
    uploads = transcript.data_path.glob("upload.*")
    for upload in uploads:
        upload.unlink(missing_ok=True)
    logger.info("Remove upload done")


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

    if transcript.audio_deleted:
        logger.info("Skipping mp3 upload - audio marked as deleted")
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
async def pipeline_title(transcript: Transcript, logger: Logger):
    logger.info("Starting title")
    runner = PipelineMainTitle(transcript_id=transcript.id)
    await runner.run()
    logger.info("Title done")


@get_transcript
async def pipeline_summaries(transcript: Transcript, logger: Logger):
    logger.info("Starting summaries")
    runner = PipelineMainFinalSummaries(transcript_id=transcript.id)
    await runner.run()
    logger.info("Summaries done")


@get_transcript
async def cleanup_consent(transcript: Transcript, logger: Logger):
    logger.info("Starting consent cleanup")

    consent_denied = False
    recording = None
    try:
        if transcript.recording_id:
            recording = await recordings_controller.get_by_id(transcript.recording_id)
            if recording and recording.meeting_id:
                meeting = await meetings_controller.get_by_id(recording.meeting_id)
                if meeting:
                    consent_denied = await meeting_consent_controller.has_any_denial(
                        meeting.id
                    )
    except Exception as e:
        logger.error(f"Failed to get fetch consent: {e}", exc_info=e)
        consent_denied = True

    if not consent_denied:
        logger.info("Consent approved, keeping all files")
        return

    logger.info("Consent denied, cleaning up all related audio files")

    if recording and recording.bucket_name and recording.object_key:
        s3_whereby = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_WHEREBY_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_WHEREBY_ACCESS_KEY_SECRET,
        )
        try:
            s3_whereby.delete_object(
                Bucket=recording.bucket_name, Key=recording.object_key
            )
            logger.info(
                f"Deleted original Whereby recording: {recording.bucket_name}/{recording.object_key}"
            )
        except Exception as e:
            logger.error(f"Failed to delete Whereby recording: {e}", exc_info=e)

    # non-transactional, files marked for deletion not actually deleted is possible
    await transcripts_controller.update(transcript, {"audio_deleted": True})
    # 2. Delete processed audio from transcript storage S3 bucket
    if transcript.audio_location == "storage":
        storage = get_transcripts_storage()
        try:
            await storage.delete_file(transcript.storage_audio_path)
            logger.info(
                f"Deleted processed audio from storage: {transcript.storage_audio_path}"
            )
        except Exception as e:
            logger.error(f"Failed to delete processed audio: {e}", exc_info=e)

    # 3. Delete local audio files
    try:
        if hasattr(transcript, "audio_mp3_filename") and transcript.audio_mp3_filename:
            transcript.audio_mp3_filename.unlink(missing_ok=True)
        if hasattr(transcript, "audio_wav_filename") and transcript.audio_wav_filename:
            transcript.audio_wav_filename.unlink(missing_ok=True)
    except Exception as e:
        logger.error(f"Failed to delete local audio files: {e}", exc_info=e)

    logger.info("Consent cleanup done")


@get_transcript
async def pipeline_post_to_zulip(transcript: Transcript, logger: Logger):
    logger.info("Starting post to zulip")

    if not transcript.recording_id:
        logger.info("Transcript has no recording")
        return

    recording = await recordings_controller.get_by_id(transcript.recording_id)
    if not recording:
        logger.info("Recording not found")
        return

    if not recording.meeting_id:
        logger.info("Recording has no meeting")
        return

    meeting = await meetings_controller.get_by_id(recording.meeting_id)
    if not meeting:
        logger.info("No meeting found for this recording")
        return

    room = await rooms_controller.get_by_id(meeting.room_id)
    if not room:
        logger.error(f"Missing room for a meeting {meeting.id}")
        return

    if room.zulip_auto_post:
        message = get_zulip_message(transcript=transcript, include_topics=True)
        message_updated = False
        if transcript.zulip_message_id:
            try:
                await update_zulip_message(
                    transcript.zulip_message_id,
                    room.zulip_stream,
                    room.zulip_topic,
                    message,
                )
                message_updated = True
            except Exception:
                logger.error(
                    f"Failed to update zulip message with id {transcript.zulip_message_id}"
                )
        if not message_updated:
            response = await send_message_to_zulip(
                room.zulip_stream, room.zulip_topic, message
            )
            await transcripts_controller.update(
                transcript, {"zulip_message_id": response["id"]}
            )

    logger.info("Posted to zulip")


# ===================================================================
# Celery tasks that can be called from the API
# ===================================================================


@shared_task
@asynctask
async def task_pipeline_remove_upload(*, transcript_id: str):
    await pipeline_remove_upload(transcript_id=transcript_id)


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
async def task_pipeline_title(*, transcript_id: str):
    await pipeline_title(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_final_summaries(*, transcript_id: str):
    await pipeline_summaries(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_cleanup_consent(*, transcript_id: str):
    await cleanup_consent(transcript_id=transcript_id)


@shared_task
@asynctask
async def task_pipeline_post_to_zulip(*, transcript_id: str):
    await pipeline_post_to_zulip(transcript_id=transcript_id)


def pipeline_post(*, transcript_id: str):
    """
    Run the post pipeline
    """
    chain_mp3_and_diarize = (
        task_pipeline_waveform.si(transcript_id=transcript_id)
        | task_pipeline_convert_to_mp3.si(transcript_id=transcript_id)
        | task_pipeline_upload_mp3.si(transcript_id=transcript_id)
        | task_pipeline_remove_upload.si(transcript_id=transcript_id)
        | task_pipeline_diarization.si(transcript_id=transcript_id)
        | task_cleanup_consent.si(transcript_id=transcript_id)
    )
    chain_title_preview = task_pipeline_title.si(transcript_id=transcript_id)
    chain_final_summaries = task_pipeline_final_summaries.si(
        transcript_id=transcript_id
    )

    chain = chord(
        group(chain_mp3_and_diarize, chain_title_preview),
        chain_final_summaries,
    ) | task_pipeline_post_to_zulip.si(transcript_id=transcript_id)

    return chain.delay()


@get_transcript
async def pipeline_process(transcript: Transcript, logger: Logger):
    try:
        if transcript.audio_location == "storage":
            await transcripts_controller.download_mp3_from_storage(transcript)
            transcript.audio_waveform_filename.unlink(missing_ok=True)
            await transcripts_controller.update(
                transcript,
                {
                    "topics": [],
                },
            )

        # open audio
        audio_filename = next(transcript.data_path.glob("upload.*"), None)
        if audio_filename and transcript.status != "uploaded":
            raise Exception("File upload is not completed")

        if not audio_filename:
            audio_filename = next(transcript.data_path.glob("audio.*"), None)
            if not audio_filename:
                raise Exception("There is no file to process")

        container = av.open(audio_filename.as_posix())

        # create pipeline
        pipeline = PipelineMainLive(transcript_id=transcript.id)
        pipeline.start()

        # push audio to pipeline
        try:
            logger.info("Start pushing audio into the pipeline")
            for frame in container.decode(audio=0):
                await pipeline.push(frame)
        finally:
            logger.info("Flushing the pipeline")
            await pipeline.flush()

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
async def task_pipeline_process(*, transcript_id: str):
    return await pipeline_process(transcript_id=transcript_id)
