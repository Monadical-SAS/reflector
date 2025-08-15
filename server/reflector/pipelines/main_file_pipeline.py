"""
File-based processing pipeline
==============================

Optimized pipeline for processing complete audio/video files.
Uses parallel processing for transcription, diarization, and waveform generation.
"""

import asyncio
import tempfile
from pathlib import Path

import av
from celery import shared_task

from reflector.db.transcripts import (
    Transcript,
    transcripts_controller,
)
from reflector.logger import logger
from reflector.pipelines.main_live_pipeline import PipelineMainBase, asynctask
from reflector.processors import (
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


class EmptyPipeline:
    """Mock pipeline for processors that need a pipeline reference"""

    logger = logger

    def get_pref(self, k, d=None):
        return d

    async def emit(self, event):
        pass


class PipelineMainFile(PipelineMainBase):
    """
    Optimized file processing pipeline.
    Processes complete audio/video files with parallel execution.
    """

    async def process_file(self, file_path: Path):
        """Main entry point for file processing"""
        self.prepare()
        log = logger.bind(transcript_id=self.transcript_id)
        log.info(f"Starting file pipeline for {file_path}")

        # Get transcript for configuration
        transcript = await self.get_transcript()

        # Extract audio if needed
        audio_path = await self.extract_audio(file_path)

        # Upload for processing
        audio_url = await self.upload_audio(audio_path, transcript)

        # Run parallel processing
        await self.run_parallel_processing(
            audio_path,
            audio_url,
            transcript.source_language,
            transcript.target_language,
        )

        log.info("File pipeline complete")

    async def extract_audio(self, file_path: Path) -> Path:
        """Extract audio from video if needed"""
        logger.info(f"Checking file type: {file_path}")

        # Check if it's already audio
        container = av.open(str(file_path))
        has_video = len(container.streams.video) > 0
        container.close()

        if not has_video:
            logger.info("File is already audio")
            return file_path

        # Extract audio to temp file
        logger.info("Extracting audio from video")
        temp_audio = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        temp_audio_path = Path(temp_audio.name)
        temp_audio.close()

        input_container = av.open(str(file_path))
        output_container = av.open(str(temp_audio_path), "w")

        audio_stream = output_container.add_stream("mp3")

        for frame in input_container.decode(audio=0):
            for packet in audio_stream.encode(frame):
                output_container.mux(packet)

        for packet in audio_stream.encode():
            output_container.mux(packet)

        input_container.close()
        output_container.close()

        return temp_audio_path

    async def upload_audio(self, audio_path: Path, transcript: Transcript) -> str:
        """Upload audio to storage for processing"""
        storage = get_transcripts_storage()

        if not storage:
            raise Exception(
                "Storage backend required for file processing. Configure TRANSCRIPT_STORAGE_* settings."
            )

        logger.info("Uploading audio to storage")

        with open(audio_path, "rb") as f:
            audio_data = f.read()

        storage_path = f"file_pipeline/{transcript.id}/audio.mp3"
        await storage.put_file(storage_path, audio_data)

        audio_url = await storage.get_file_url(storage_path)

        logger.info(f"Audio uploaded to {audio_url}")
        return audio_url

    async def run_parallel_processing(
        self,
        audio_path: Path,
        audio_url: str,
        source_language: str,
        target_language: str,
    ):
        """Coordinate parallel processing of transcription, diarization, and waveform"""
        logger.info("Starting parallel processing", transcript_id=self.transcript_id)

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
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                task_names = ["transcription", "diarization", "waveform"]
                logger.error(
                    f"Error in {task_names[i]}: {result}",
                    transcript_id=self.transcript_id,
                )
                raise result

        # Phase 2: Assemble transcript with diarization
        logger.info(
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
        logger.info("Generating topics", transcript_id=self.transcript_id)
        topics = await self.detect_topics(diarized_transcript, target_language)

        # Phase 4: Generate title and summaries in parallel
        logger.info("Generating title and summaries", transcript_id=self.transcript_id)
        await asyncio.gather(
            self.generate_title(topics),
            self.generate_summaries(topics),
            return_exceptions=True,
        )

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
            logger.info("Diarization disabled")
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
            logger.error(f"Diarization failed: {e}")
            return None

    async def generate_waveform(self, audio_path: Path):
        """Generate and save waveform"""
        transcript = await self.get_transcript()

        processor = AudioWaveformProcessor(
            audio_path=audio_path,
            waveform_path=transcript.audio_waveform_filename,
            on_waveform=self.on_waveform,
        )

        processor.pipeline = EmptyPipeline()

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

        topic_detector = TranscriptTopicDetectorProcessor(callback=self.on_topic)
        topic_detector.pipeline = EmptyPipeline()

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
            logger.warning("No topics for title generation")
            return

        processor = TranscriptFinalTitleProcessor(callback=self.on_title)
        processor.set_pipeline(self)

        for topic in topics:
            await processor.push(topic)

        await processor.flush()

    async def generate_summaries(self, topics: list[TitleSummary]):
        """Generate long and short summaries from topics"""
        if not topics:
            logger.warning("No topics for summary generation")
            return

        transcript = await self.get_transcript()
        processor = TranscriptFinalSummaryProcessor(
            transcript=transcript,
            callback=self.on_long_summary,
            on_short_summary=self.on_short_summary,
        )
        processor.set_pipeline(self)

        for topic in topics:
            await processor.push(topic)

        await processor.flush()


@shared_task
@asynctask
async def task_pipeline_file_process(*, transcript_id: str):
    """Celery task for file pipeline processing"""

    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        raise Exception(f"Transcript {transcript_id} not found")

    # Find the file to process
    audio_file = next(transcript.data_path.glob("upload.*"), None)
    if not audio_file:
        audio_file = next(transcript.data_path.glob("audio.*"), None)

    if not audio_file:
        raise Exception("No audio file found to process")

    # Run file pipeline
    pipeline = PipelineMainFile(transcript_id=transcript_id)
    await pipeline.process_file(audio_file)
