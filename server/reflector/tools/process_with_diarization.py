"""
Process audio file with diarization support
===========================================

Extended version of process.py that includes speaker diarization.
This tool processes audio files locally without requiring the full server infrastructure.
"""

import asyncio
import tempfile
from pathlib import Path
from typing import Optional, List

import av
from reflector.logger import logger
from reflector.processors import (
    AudioChunkerProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    AudioFileWriterProcessor,
    Pipeline,
    PipelineEvent,
    TranscriptFinalSummaryProcessor,
    TranscriptFinalTitleProcessor,
    TranscriptLinerProcessor,
    TranscriptTopicDetectorProcessor,
    TranscriptTranslatorProcessor,
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
            transcript=data.transcript
        )
        self.topics.append(topic_with_id)
        
        # Pass through the original topic
        await self.emit(data)
    
    def get_topics(self) -> List[TitleSummaryWithId]:
        return self.topics




async def process_audio_file_with_diarization(
    filename,
    event_callback,
    only_transcript=False,
    source_language="en",
    target_language="en",
    enable_diarization=True,
    diarization_backend="local",
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
        AudioChunkerProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(),
    ]
    
    processors += [
        TranscriptLinerProcessor(),
        TranscriptTranslatorProcessor.as_threaded(),
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
            logger.info(f"Starting diarization phase with {len(topics)} topics")
            
            try:
                # Import diarization processor
                if diarization_backend == "local":
                    # This will automatically register the local backend
                    import reflector.processors.audio_diarization_local
                
                from reflector.processors import AudioDiarizationAutoProcessor
                
                # Create diarization processor
                diarization_processor = AudioDiarizationAutoProcessor(name=diarization_backend)
                diarization_processor.on(event_callback)
                
                # Create diarization input
                diarization_input = AudioDiarizationInput(
                    audio_url=audio_temp_path,  # Local file path
                    topics=topics
                )
                
                # Run diarization
                logger.info(f"Running diarization with backend: {diarization_backend}")
                await diarization_processor.push(diarization_input)
                await diarization_processor.flush()
                
                # Count speakers found
                speakers_found = set()
                for topic in topics:
                    if topic.transcript and topic.transcript.words:
                        for word in topic.transcript.words:
                            if hasattr(word, 'speaker') and word.speaker is not None:
                                speakers_found.add(word.speaker)
                
                logger.info(f"Diarization complete. Found {len(speakers_found)} speakers: {sorted(speakers_found)}")
                
            except ImportError as e:
                logger.error(f"Failed to import diarization dependencies: {e}")
                logger.error("Install with: uv pip install pyannote.audio torch torchaudio")
                logger.error("And set HF_TOKEN environment variable for pyannote models")
            except Exception as e:
                logger.error(f"Diarization failed: {e}")
                logger.error("Continuing without speaker information")
        else:
            logger.warning("Skipping diarization: no topics available")
    
    # Clean up temp file
    if audio_temp_path:
        try:
            Path(audio_temp_path).unlink()
            logger.debug(f"Cleaned up temporary audio file: {audio_temp_path}")
        except Exception as e:
            logger.warning(f"Failed to clean up temp file {audio_temp_path}: {e}")

    logger.info("All done!")


if __name__ == "__main__":
    import argparse
    import os

    parser = argparse.ArgumentParser(
        description="Process audio files with optional speaker diarization"
    )
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    parser.add_argument("--only-transcript", "-t", action="store_true",
                       help="Only generate transcript without topics/summaries")
    parser.add_argument("--source-language", default="en",
                       help="Source language code (default: en)")
    parser.add_argument("--target-language", default="en",
                       help="Target language code (default: en)")
    parser.add_argument("--output", "-o", help="Output file (output.jsonl)")
    parser.add_argument("--enable-diarization", "-d", action="store_true",
                       help="Enable speaker diarization")
    parser.add_argument("--diarization-backend", default="local",
                       choices=["local", "modal"],
                       help="Diarization backend to use (default: local)")
    args = parser.parse_args()
    
    # Set REDIS_HOST to localhost if not provided
    if "REDIS_HOST" not in os.environ:
        os.environ["REDIS_HOST"] = "localhost"
        logger.info("REDIS_HOST not set, defaulting to localhost")

    output_fd = None
    if args.output:
        output_fd = open(args.output, "w")

    async def event_callback(event: PipelineEvent):
        processor = event.processor
        # Ignore internal processors
        if processor in ("AudioChunkerProcessor", "AudioMergeProcessor", 
                        "AudioFileWriterProcessor", "TopicCollectorProcessor",
                        "BroadcastProcessor"):
            return
        logger.info(f"Event: {event.processor} - {type(event.data).__name__}")
        if output_fd:
            output_fd.write(event.model_dump_json())
            output_fd.write("\n")
            output_fd.flush()  # Ensure data is written immediately

    asyncio.run(
        process_audio_file_with_diarization(
            args.source,
            event_callback,
            only_transcript=args.only_transcript,
            source_language=args.source_language,
            target_language=args.target_language,
            enable_diarization=args.enable_diarization,
            diarization_backend=args.diarization_backend,
        )
    )

    if output_fd:
        output_fd.close()
        logger.info(f"Output written to {args.output}")