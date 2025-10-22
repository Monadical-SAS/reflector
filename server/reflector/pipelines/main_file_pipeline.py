"""
File-based processing pipeline
==============================

Optimized pipeline for processing complete audio/video files.
Uses parallel processing for transcription, diarization, and waveform generation.
"""

import asyncio
import uuid
from pathlib import Path

import av
import structlog
from celery import chain, shared_task

from reflector.asynctask import asynctask
from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import (
    SourceKind,
    Transcript,
    TranscriptStatus,
    transcripts_controller,
)
from reflector.logger import logger
from reflector.pipelines.main_live_pipeline import (
    PipelineMainBase,
    broadcast_to_sockets,
    task_cleanup_consent,
    task_pipeline_post_to_zulip,
)
from reflector.processors import (
    AudioFileWriterProcessor,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptTopicDetectorProcessor,
)
from reflector.processors.audio_waveform_processor import AudioWaveformProcessor
from reflector.processors.file_diarization import FileDiarizationInput
from reflector.processors.file_diarization_auto import FileDiarizationAutoProcessor
from reflector.processors.file_transcript import FileTranscriptInput
from reflector.processors.file_transcript_auto import FileTranscriptAutoProcessor
from reflector.processors.transcript_diarization_assembler import (
    TranscriptDiarizationAssemblerInput,
    TranscriptDiarizationAssemblerProcessor,
)
from reflector.processors.types import (
    DiarizationSegment,
    TitleSummary,
)
from reflector.processors.types import (
    Transcript as TranscriptType,
)
from reflector.settings import settings
from reflector.storage import get_transcripts_storage
from reflector.worker.webhook import send_transcript_webhook


class EmptyPipeline:
    """Empty pipeline for processors that need a pipeline reference"""

    def __init__(self, logger: structlog.BoundLogger):
        self.logger = logger

    def get_pref(self, k, d=None):
        return d

    async def emit(self, event):
        pass


class PipelineMainFile(PipelineMainBase):
    """
    Optimized file processing pipeline.
    Processes complete audio/video files with parallel execution.
    """

    logger: structlog.BoundLogger = None
    empty_pipeline = None

    def __init__(self, transcript_id: str):
        super().__init__(transcript_id=transcript_id)
        self.logger = logger.bind(transcript_id=self.transcript_id)
        self.empty_pipeline = EmptyPipeline(logger=self.logger)

    def _handle_gather_exceptions(self, results: list, operation: str) -> None:
        """Handle exceptions from asyncio.gather with return_exceptions=True"""
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                continue
            self.logger.error(
                f"Error in {operation} (task {i}): {result}",
                transcript_id=self.transcript_id,
                exc_info=result,
            )

    @broadcast_to_sockets
    async def set_status(self, transcript_id: str, status: TranscriptStatus):
        async with self.lock_transaction():
            return await transcripts_controller.set_status(transcript_id, status)

    async def process(self, file_path: Path):
        """Main entry point for file processing"""
        self.logger.info(f"Starting file pipeline for {file_path}")

        transcript = await self.get_transcript()

        # Clear transcript as we're going to regenerate everything
        async with self.transaction():
            await transcripts_controller.update(
                transcript,
                {
                    "events": [],
                    "topics": [],
                },
            )

        # Extract audio and write to transcript location
        audio_path = await self.extract_and_write_audio(file_path, transcript)

        # Upload for processing
        audio_url = await self.upload_audio(audio_path, transcript)

        # Run parallel processing
        await self.run_parallel_processing(
            audio_path,
            audio_url,
            transcript.source_language,
            transcript.target_language,
        )

        self.logger.info("File pipeline complete")

        await self.set_status(transcript.id, "ended")

    async def extract_and_write_audio(
        self, file_path: Path, transcript: Transcript
    ) -> Path:
        """Extract audio from video if needed and write to transcript location as MP3"""
        self.logger.info(f"Processing audio file: {file_path}")

        # Check if it's already audio-only
        container = av.open(str(file_path))
        has_video = len(container.streams.video) > 0
        container.close()

        # Use AudioFileWriterProcessor to write MP3 to transcript location
        mp3_writer = AudioFileWriterProcessor(
            path=transcript.audio_mp3_filename,
            on_duration=self.on_duration,
        )

        # Process audio frames and write to transcript location
        input_container = av.open(str(file_path))
        for frame in input_container.decode(audio=0):
            await mp3_writer.push(frame)

        await mp3_writer.flush()
        input_container.close()

        if has_video:
            self.logger.info(
                f"Extracted audio from video and saved to {transcript.audio_mp3_filename}"
            )
        else:
            self.logger.info(
                f"Converted audio file and saved to {transcript.audio_mp3_filename}"
            )

        return transcript.audio_mp3_filename

    async def upload_audio(self, audio_path: Path, transcript: Transcript) -> str:
        """Upload audio to storage for processing"""
        storage = get_transcripts_storage()

        if not storage:
            raise Exception(
                "Storage backend required for file processing. Configure TRANSCRIPT_STORAGE_* settings."
            )

        self.logger.info("Uploading audio to storage")

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        storage_path = f"file_pipeline/{transcript.id}/audio.mp3"
        await storage.put_file(storage_path, audio_data)

        audio_url = await storage.get_file_url(storage_path)

        self.logger.info(f"Audio uploaded to {audio_url}")
        return audio_url

    async def run_parallel_processing(
        self,
        audio_path: Path,
        audio_url: str,
        source_language: str,
        target_language: str,
    ):
        """Coordinate parallel processing of transcription, diarization, and waveform"""
        self.logger.info(
            "Starting parallel processing", transcript_id=self.transcript_id
        )

        # Phase 1: Parallel processing of independent tasks
        transcription_task = self.transcribe_file(audio_url, source_language)
        diarization_task = self.diarize_file(audio_url)
        waveform_task = self.generate_waveform(audio_path)

        results = await asyncio.gather(
            transcription_task, diarization_task, waveform_task, return_exceptions=True
        )

        transcript_result = results[0]
        diarization_result = results[1]

        # Handle errors - raise any exception that occurred
        self._handle_gather_exceptions(results, "parallel processing")
        for result in results:
            if isinstance(result, Exception):
                raise result

        # Phase 2: Assemble transcript with diarization
        self.logger.info(
            "Assembling transcript with diarization", transcript_id=self.transcript_id
        )
        processor = TranscriptDiarizationAssemblerProcessor()
        input_data = TranscriptDiarizationAssemblerInput(
            transcript=transcript_result, diarization=diarization_result or []
        )

        # Store result for retrieval
        diarized_transcript: Transcript | None = None

        async def capture_result(transcript):
            nonlocal diarized_transcript
            diarized_transcript = transcript

        processor.on(capture_result)
        await processor.push(input_data)
        await processor.flush()

        if not diarized_transcript:
            raise ValueError("No diarized transcript captured")

        # Phase 3: Generate topics from diarized transcript
        self.logger.info("Generating topics", transcript_id=self.transcript_id)
        topics = await self.detect_topics(diarized_transcript, target_language)

        # Phase 4: Generate title and summaries in parallel
        self.logger.info(
            "Generating title and summaries", transcript_id=self.transcript_id
        )
        results = await asyncio.gather(
            self.generate_title(topics),
            self.generate_summaries(topics),
            return_exceptions=True,
        )

        self._handle_gather_exceptions(results, "title and summary generation")

    async def transcribe_file(self, audio_url: str, language: str) -> TranscriptType:
        """Transcribe complete file"""
        processor = FileTranscriptAutoProcessor()
        input_data = FileTranscriptInput(audio_url=audio_url, language=language)

        # Store result for retrieval
        result: TranscriptType | None = None

        async def capture_result(transcript):
            nonlocal result
            result = transcript

        processor.on(capture_result)
        await processor.push(input_data)
        await processor.flush()

        if not result:
            raise ValueError("No transcript captured")

        return result

    async def diarize_file(self, audio_url: str) -> list[DiarizationSegment] | None:
        """Get diarization for file"""
        if not settings.DIARIZATION_BACKEND:
            self.logger.info("Diarization disabled")
            return None

        processor = FileDiarizationAutoProcessor()
        input_data = FileDiarizationInput(audio_url=audio_url)

        # Store result for retrieval
        result = None

        async def capture_result(diarization_output):
            nonlocal result
            result = diarization_output.diarization

        try:
            processor.on(capture_result)
            await processor.push(input_data)
            await processor.flush()
            return result
        except Exception as e:
            self.logger.error(f"Diarization failed: {e}")
            return None

    async def generate_waveform(self, audio_path: Path):
        """Generate and save waveform"""
        transcript = await self.get_transcript()

        processor = AudioWaveformProcessor(
            audio_path=audio_path,
            waveform_path=transcript.audio_waveform_filename,
            on_waveform=self.on_waveform,
        )
        processor.set_pipeline(self.empty_pipeline)

        await processor.flush()

    async def detect_topics(
        self, transcript: TranscriptType, target_language: str
    ) -> list[TitleSummary]:
        """Detect topics from complete transcript"""
        chunk_size = 300
        topics: list[TitleSummary] = []

        async def on_topic(topic: TitleSummary):
            topics.append(topic)
            return await self.on_topic(topic)

        topic_detector = TranscriptTopicDetectorProcessor(callback=on_topic)
        topic_detector.set_pipeline(self.empty_pipeline)

        for i in range(0, len(transcript.words), chunk_size):
            chunk_words = transcript.words[i : i + chunk_size]
            if not chunk_words:
                continue

            chunk_transcript = TranscriptType(
                words=chunk_words, translation=transcript.translation
            )

            await topic_detector.push(chunk_transcript)

        await topic_detector.flush()
        return topics

    async def generate_title(self, topics: list[TitleSummary]):
        """Generate title from topics"""
        if not topics:
            self.logger.warning("No topics for title generation")
            return

        processor = TranscriptFinalTitleProcessor(callback=self.on_title)
        processor.set_pipeline(self.empty_pipeline)

        for topic in topics:
            await processor.push(topic)

        await processor.flush()

    async def generate_summaries(self, topics: list[TitleSummary]):
        """Generate long and short summaries from topics"""
        if not topics:
            self.logger.warning("No topics for summary generation")
            return

        transcript = await self.get_transcript()
        processor = TranscriptFinalSummaryProcessor(
            transcript=transcript,
            callback=self.on_long_summary,
            on_short_summary=self.on_short_summary,
        )
        processor.set_pipeline(self.empty_pipeline)

        for topic in topics:
            await processor.push(topic)

        await processor.flush()


@shared_task
@asynctask
async def task_send_webhook_if_needed(*, transcript_id: str):
    """Send webhook if this is a room recording with webhook configured"""
    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        return

    if transcript.source_kind == SourceKind.ROOM and transcript.room_id:
        room = await rooms_controller.get_by_id(transcript.room_id)
        if room and room.webhook_url:
            logger.info(
                "Dispatching webhook",
                transcript_id=transcript_id,
                room_id=room.id,
                webhook_url=room.webhook_url,
            )
            send_transcript_webhook.delay(
                transcript_id, room.id, event_id=uuid.uuid4().hex
            )


@shared_task
@asynctask
async def task_pipeline_file_process(*, transcript_id: str):
    """Celery task for file pipeline processing"""

    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise Exception(f"Transcript {transcript_id} not found")

    pipeline = PipelineMainFile(transcript_id=transcript_id)
    try:
        await pipeline.set_status(transcript_id, "processing")

        # Find the file to process
        audio_file = next(transcript.data_path.glob("upload.*"), None)
        if not audio_file:
            audio_file = next(transcript.data_path.glob("audio.*"), None)

        if not audio_file:
            raise Exception("No audio file found to process")

        await pipeline.process(audio_file)

    except Exception as e:
        logger.error(
            f"File pipeline failed for transcript {transcript_id}: {type(e).__name__}: {str(e)}",
            exc_info=True,
            transcript_id=transcript_id,
        )
        await pipeline.set_status(transcript_id, "error")
        raise

    # Run post-processing chain: consent cleanup -> zulip -> webhook
    post_chain = chain(
        task_cleanup_consent.si(transcript_id=transcript_id),
        task_pipeline_post_to_zulip.si(transcript_id=transcript_id),
        task_send_webhook_if_needed.si(transcript_id=transcript_id),
    )
    post_chain.delay()
