"""
Process audio file with diarization support
===========================================

Extended version of process.py that includes speaker diarization.
This tool processes audio files locally without requiring the full server infrastructure.
"""

import asyncio
import tempfile
import uuid
from pathlib import Path
from typing import List

import av

from reflector.logger import logger
from reflector.processors import (
    AudioChunkerAutoProcessor,
    AudioDownscaleProcessor,
    AudioFileWriterProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    Pipeline,
    PipelineEvent,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptTranslatorAutoProcessor,
)
from reflector.processors.base import BroadcastProcessor, Processor
from reflector.processors.types import (
    AudioDiarizationInput,
    TitleSummary,
    TitleSummaryWithId,
)


class TopicCollectorProcessor(Processor):
    """Collect topics for diarization"""

    INPUT_TYPE = TitleSummary
    OUTPUT_TYPE = TitleSummary

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.topics: List[TitleSummaryWithId] = []
        self._topic_id = 0

    async def _push(self, data: TitleSummary):
        # Convert to TitleSummaryWithId and collect
        self._topic_id += 1
        topic_with_id = TitleSummaryWithId(
            id=str(self._topic_id),
            title=data.title,
            summary=data.summary,
            timestamp=data.timestamp,
            duration=data.duration,
            transcript=data.transcript,
        )
        self.topics.append(topic_with_id)

        # Pass through the original topic
        await self.emit(data)

    def get_topics(self) -> List[TitleSummaryWithId]:
        return self.topics


async def process_audio_file(
    filename,
    event_callback,
    only_transcript=False,
    source_language="en",
    target_language="en",
    enable_diarization=True,
    diarization_backend="pyannote",
):
    # Create temp file for audio if diarization is enabled
    audio_temp_path = None
    if enable_diarization:
        audio_temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        audio_temp_path = audio_temp_file.name
        audio_temp_file.close()

    # Create processor for collecting topics
    topic_collector = TopicCollectorProcessor()

    # Build pipeline for audio processing
    processors = []

    # Add audio file writer at the beginning if diarization is enabled
    if enable_diarization:
        processors.append(AudioFileWriterProcessor(audio_temp_path))

    # Add the rest of the processors
    processors += [
        AudioDownscaleProcessor(),
        AudioChunkerAutoProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(),
        TranscriptLinerProcessor(),
        TranscriptTranslatorAutoProcessor.as_threaded(),
    ]

    if not only_transcript:
        processors += [
            TranscriptTopicDetectorProcessor.as_threaded(),
            # Collect topics for diarization
            topic_collector,
            BroadcastProcessor(
                processors=[
                    TranscriptFinalTitleProcessor.as_threaded(),
                    TranscriptFinalSummaryProcessor.as_threaded(),
                ],
            ),
        ]

    # Create main pipeline
    pipeline = Pipeline(*processors)
    pipeline.set_pref("audio:source_language", source_language)
    pipeline.set_pref("audio:target_language", target_language)
    pipeline.describe()
    pipeline.on(event_callback)

    # Start processing audio
    logger.info(f"Opening {filename}")
    container = av.open(filename)
    try:
        logger.info("Start pushing audio into the pipeline")
        for frame in container.decode(audio=0):
            await pipeline.push(frame)
    finally:
        logger.info("Flushing the pipeline")
        await pipeline.flush()

    # Run diarization if enabled and we have topics
    if enable_diarization and not only_transcript and audio_temp_path:
        topics = topic_collector.get_topics()

        if topics:
            logger.info(f"Starting diarization with {len(topics)} topics")

            try:
                from reflector.processors import AudioDiarizationAutoProcessor

                diarization_processor = AudioDiarizationAutoProcessor(
                    name=diarization_backend
                )

                diarization_processor.set_pipeline(pipeline)

                # For Modal backend, we need to upload the file to S3 first
                if diarization_backend == "modal":
                    from datetime import datetime

                    from reflector.storage import get_transcripts_storage
                    from reflector.utils.s3_temp_file import S3TemporaryFile

                    storage = get_transcripts_storage()

                    # Generate a unique filename in evaluation folder
                    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                    audio_filename = f"evaluation/diarization_temp/{timestamp}_{uuid.uuid4().hex}.wav"

                    # Use context manager for automatic cleanup
                    async with S3TemporaryFile(storage, audio_filename) as s3_file:
                        # Read and upload the audio file
                        with open(audio_temp_path, "rb") as f:
                            audio_data = f.read()

                        audio_url = await s3_file.upload(audio_data)
                        logger.info(f"Uploaded audio to S3: {audio_filename}")

                        # Create diarization input with S3 URL
                        diarization_input = AudioDiarizationInput(
                            audio_url=audio_url, topics=topics
                        )

                        # Run diarization
                        await diarization_processor.push(diarization_input)
                        await diarization_processor.flush()

                        logger.info("Diarization complete")
                        # File will be automatically cleaned up when exiting the context
                else:
                    # For local backend, use local file path
                    audio_url = audio_temp_path

                    # Create diarization input
                    diarization_input = AudioDiarizationInput(
                        audio_url=audio_url, topics=topics
                    )

                    # Run diarization
                    await diarization_processor.push(diarization_input)
                    await diarization_processor.flush()

                    logger.info("Diarization complete")

            except ImportError as e:
                logger.error(f"Failed to import diarization dependencies: {e}")
                logger.error(
                    "Install with: uv pip install pyannote.audio torch torchaudio"
                )
                logger.error(
                    "And set HF_TOKEN environment variable for pyannote models"
                )
                raise SystemExit(1)
            except Exception as e:
                logger.error(f"Diarization failed: {e}")
                raise SystemExit(1)
        else:
            logger.warning("Skipping diarization: no topics available")

    # Clean up temp file
    if audio_temp_path:
        try:
            Path(audio_temp_path).unlink()
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {audio_temp_path}: {e}")

    logger.info("All done!")


async def process_file_pipeline(
    filename: str,
    event_callback,
    source_language="en",
    target_language="en",
    enable_diarization=True,
    diarization_backend="modal",
    output_fd=None,
):
    """Process audio/video file using the optimized file pipeline"""
    try:
        from reflector.db import get_database
        from reflector.db.transcripts import SourceKind, transcripts_controller
        from reflector.pipelines.main_live_pipeline import PipelineMainLive
        import av

        database = get_database()
        await database.connect()
        try:
            # Create a temporary transcript for processing
            transcript = await transcripts_controller.add(
                "",
                source_kind=SourceKind.FILE,
                source_language=source_language,
                target_language=target_language,
            )

            # Copy file to transcript data path as upload.* to match UI flow
            from shutil import copy
            extension = Path(filename).suffix[1:]  # Remove the dot
            
            # Ensure data directory exists
            transcript.data_path.mkdir(parents=True, exist_ok=True)
            
            upload_path = transcript.data_path / f"upload.{extension}"
            copy(filename, upload_path)
            
            # Update status to uploaded
            await transcripts_controller.update(transcript, {"status": "uploaded"})

            # Process the file using PipelineMainLive (same as UI)
            pipeline = PipelineMainLive(transcript_id=transcript.id)
            pipeline.start()
            
            # Open and push audio to pipeline
            container = av.open(str(upload_path))
            try:
                logger.info("Start pushing audio into the pipeline")
                for frame in container.decode(audio=0):
                    await pipeline.push(frame)
            finally:
                logger.info("Flushing the pipeline")
                await pipeline.flush()
                container.close()
                
            logger.info("Waiting for the pipeline to end")
            await pipeline.join()

            logger.info("File pipeline processing complete")
            
            # Output events (to match stream pipeline behavior)
            # Get final transcript with all events
            final_transcript = await transcripts_controller.get_by_id(transcript.id)
            if not final_transcript.events:
                logger.error("CRITICAL ERROR: No events were generated during processing")
                raise RuntimeError("Processing failed: No events were captured")
            
            # Define processors to ignore (same as original stream pipeline)
            # These would be the uppercase event names if they were stored
            IGNORED_PROCESSORS = {
                "AUDIO_DOWNSCALE",
                "AUDIO_CHUNKER", 
                "AUDIO_MERGE",
                "AUDIO_FILE_WRITER",
                "TOPIC_COLLECTOR",
                "BROADCAST",
            }
            
            for event_data in final_transcript.events:
                # event_data is a TranscriptEvent object with 'event' and 'data' attributes
                processor = event_data.event if hasattr(event_data, 'event') else "Unknown"
                data = event_data.data if hasattr(event_data, 'data') else {}
                
                # Skip ignored processors (matching original behavior)
                if processor in IGNORED_PROCESSORS:
                    continue
                
                # Log to stdout (matching original format)
                # For database events, show what kind of data it contains
                if processor == "TRANSCRIPT" and isinstance(data, dict) and "text" in data:
                    logger.info(f"Event: {processor} - text: {data['text'][:50]}...")
                elif processor == "TOPIC" and isinstance(data, dict):
                    word_count = len(data.get("words", []))
                    logger.info(f"Event: {processor} - {word_count} words")
                elif processor == "STATUS" and isinstance(data, dict) and "value" in data:
                    logger.info(f"Event: {processor} - {data['value']}")
                elif processor == "DURATION" and isinstance(data, dict) and "duration" in data:
                    logger.info(f"Event: {processor} - {data['duration']}ms")
                elif processor == "WAVEFORM" and isinstance(data, dict) and "waveform" in data:
                    logger.info(f"Event: {processor} - {len(data['waveform'])} samples")
                else:
                    # Fallback for unknown event types
                    logger.info(f"Event: {processor}")
                
                # Write to output file if specified
                if output_fd:
                    event = PipelineEvent(
                        processor=processor,
                        uid=transcript.id,
                        data=data
                    )
                    output_fd.write(event.model_dump_json())
                    output_fd.write("\n")
                    output_fd.flush()

        finally:
            await database.disconnect()
    except ImportError as e:
        logger.error(f"File pipeline not available: {e}")
        logger.info("Falling back to stream pipeline")
        # Fall back to stream pipeline
        await process_audio_file(
            filename,
            event_callback,
            only_transcript=False,
            source_language=source_language,
            target_language=target_language,
            enable_diarization=enable_diarization,
            diarization_backend=diarization_backend,
        )


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Process audio files with optional speaker diarization"
    )
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Use streaming pipeline (original frame-based processing)",
    )
    parser.add_argument(
        "--only-transcript",
        "-t",
        action="store_true",
        help="Only generate transcript without topics/summaries",
    )
    parser.add_argument(
        "--source-language", default="en", help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target-language", default="en", help="Target language code (default: en)"
    )
    parser.add_argument("--output", "-o", help="Output file (output.jsonl)")
    parser.add_argument(
        "--enable-diarization",
        "-d",
        action="store_true",
        help="Enable speaker diarization",
    )
    parser.add_argument(
        "--diarization-backend",
        default="pyannote",
        choices=["pyannote", "modal"],
        help="Diarization backend to use (default: pyannote)",
    )
    args = parser.parse_args()

    if "REDIS_HOST" not in os.environ:
        os.environ["REDIS_HOST"] = "localhost"

    output_fd = None
    if args.output:
        output_fd = open(args.output, "w")

    async def event_callback(event: PipelineEvent):
        processor = event.processor
        data = event.data

        # Ignore internal processors
        if processor in (
            "AudioDownscaleProcessor",
            "AudioChunkerAutoProcessor",
            "AudioMergeProcessor",
            "AudioFileWriterProcessor",
            "TopicCollectorProcessor",
            "BroadcastProcessor",
        ):
            return

        # If diarization is enabled, skip the original topic events from the pipeline
        # The diarization processor will emit the same topics but with speaker info
        if processor == "TranscriptTopicDetectorProcessor" and args.enable_diarization:
            return

        # Log all events
        logger.info(f"Event: {processor} - {type(data).__name__}")

        # Write to output
        if output_fd:
            output_fd.write(event.model_dump_json())
            output_fd.write("\n")
            output_fd.flush()

    if args.stream:
        # Use original streaming pipeline
        asyncio.run(
            process_audio_file(
                args.source,
                event_callback,
                only_transcript=args.only_transcript,
                source_language=args.source_language,
                target_language=args.target_language,
                enable_diarization=args.enable_diarization,
                diarization_backend=args.diarization_backend,
            )
        )
    else:
        # Use optimized file pipeline (default)
        asyncio.run(
            process_file_pipeline(
                args.source,
                event_callback,
                source_language=args.source_language,
                target_language=args.target_language,
                enable_diarization=args.enable_diarization,
                diarization_backend=args.diarization_backend,
                output_fd=output_fd,
            )
        )

    if output_fd:
        output_fd.close()
        logger.info(f"Output written to {args.output}")
