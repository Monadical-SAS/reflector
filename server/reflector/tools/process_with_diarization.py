"""
Process audio file with diarization support
===========================================

Extended version of process.py that includes speaker diarization.
This tool processes audio files locally without requiring the full server infrastructure.
"""

import asyncio
import sys
import tempfile
import uuid
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
    logger.info(f"[DIARIZATION CHECK] enable_diarization={enable_diarization}, only_transcript={only_transcript}, audio_temp_path={audio_temp_path}")
    if enable_diarization and not only_transcript and audio_temp_path:
        topics = topic_collector.get_topics()
        logger.info(f"[DIARIZATION CHECK] Collected {len(topics)} topics")
        
        if topics:
            logger.info(f"[DIARIZATION] Starting diarization phase with {len(topics)} topics")
            
            try:
                # Import diarization processor
                if diarization_backend == "local":
                    # This will automatically register the local backend
                    import reflector.processors.audio_diarization_local
                
                from reflector.processors import AudioDiarizationAutoProcessor
                
                # Create diarization processor
                diarization_processor = AudioDiarizationAutoProcessor(name=diarization_backend)
                logger.info(f"Created diarization processor: {diarization_processor.__class__.__name__}, name={getattr(diarization_processor, 'name', 'unknown')}")
                
                # Count callback invocations
                callback_count = 0
                
                # Create a wrapper callback that handles raw data from diarization
                async def diarization_callback(data):
                    nonlocal callback_count
                    callback_count += 1
                    logger.info(f"[DIARIZATION CALLBACK] #{callback_count} triggered with data type: {type(data).__name__}")
                    if hasattr(data, 'title'):
                        logger.info(f"[DIARIZATION CALLBACK] Processing topic: {data.title[:50]}...")
                    if hasattr(data, 'id'):
                        logger.info(f"[DIARIZATION CALLBACK] Topic ID: {data.id}")
                    
                    # Check if this has speaker info
                    if hasattr(data, 'transcript') and data.transcript and data.transcript.words:
                        has_speakers = any(hasattr(w, 'speaker') and w.speaker is not None 
                                         for w in data.transcript.words[:5])  # Check first 5 words
                        logger.info(f"[DIARIZATION CALLBACK] Has speaker info: {has_speakers}")
                    
                    # Diarization processor emits raw TitleSummaryWithId objects
                    # Wrap them in PipelineEvent for consistency
                    processor_name = diarization_processor.__class__.__name__
                    logger.info(f"[DIARIZATION CALLBACK] Creating PipelineEvent with processor: {processor_name}")
                    
                    wrapped_event = PipelineEvent(
                        processor=processor_name,
                        uid=str(uuid.uuid4()),
                        data=data
                    )
                    logger.info(f"[DIARIZATION CALLBACK] Passing wrapped event to main callback")
                    await event_callback(wrapped_event)
                    logger.info(f"[DIARIZATION CALLBACK] Event callback completed")
                
                diarization_processor.on(diarization_callback)
                
                # For Modal backend, we need to upload the file to S3 first
                audio_url = audio_temp_path
                s3_audio_filename = None  # Track for cleanup
                storage = None  # Track storage instance for cleanup
                if diarization_backend == "modal":
                    try:
                        from reflector.storage import get_transcripts_storage
                        storage = get_transcripts_storage()
                        
                        # Read the audio file
                        with open(audio_temp_path, 'rb') as f:
                            audio_data = f.read()
                        
                        # Generate a unique filename in evaluation folder
                        import os
                        from datetime import datetime
                        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
                        audio_filename = f"evaluation/diarization_temp/{timestamp}_{uuid.uuid4().hex}.wav"
                        
                        # Upload to S3
                        logger.info(f"[DIARIZATION] Uploading audio to S3: {audio_filename}")
                        await storage.put_file(audio_filename, audio_data)
                        
                        # Get the public URL
                        audio_url = await storage.get_file_url(audio_filename)
                        logger.info(f"[DIARIZATION] Audio uploaded to: {audio_url}")
                        
                        # Store filename for cleanup later
                        s3_audio_filename = audio_filename
                    except Exception as e:
                        logger.error(f"[DIARIZATION] Failed to upload audio to S3: {e}")
                        raise
                
                # Create diarization input
                diarization_input = AudioDiarizationInput(
                    audio_url=audio_url,  # S3 URL for Modal, local path for local backend
                    topics=topics
                )
                
                # Run diarization
                logger.info(f"[DIARIZATION] Starting diarization with backend: {diarization_backend}")
                logger.info(f"[DIARIZATION] Processing {len(topics)} topics for diarization")
                logger.info(f"[DIARIZATION] Audio file: {audio_temp_path}")
                
                try:
                    await diarization_processor.push(diarization_input)
                    logger.info(f"[DIARIZATION] Push completed")
                    await diarization_processor.flush()
                    logger.info(f"[DIARIZATION] Flush completed")
                except Exception as e:
                    logger.error(f"[DIARIZATION] Error during processing: {e}")
                    raise
                
                # Count speakers found
                speakers_found = set()
                topics_with_speakers = 0
                for topic in topics:
                    topic_has_speaker = False
                    if topic.transcript and topic.transcript.words:
                        for word in topic.transcript.words:
                            if hasattr(word, 'speaker') and word.speaker is not None:
                                speakers_found.add(word.speaker)
                                topic_has_speaker = True
                    if topic_has_speaker:
                        topics_with_speakers += 1
                        logger.debug(f"[DIARIZATION] Topic '{topic.title[:30]}...' has speaker info")
                
                logger.info(f"[DIARIZATION] Complete. Found {len(speakers_found)} speakers: {sorted(speakers_found)}")
                logger.info(f"[DIARIZATION] {topics_with_speakers}/{len(topics)} topics have speaker info")
                logger.info(f"[DIARIZATION] Callback was invoked {callback_count} times")
                
                # Clean up S3 file if we uploaded one
                if s3_audio_filename and diarization_backend == "modal":
                    try:
                        logger.info(f"[DIARIZATION] Cleaning up S3 file: {s3_audio_filename}")
                        await storage.delete_file(s3_audio_filename)
                    except Exception as e:
                        logger.warning(f"[DIARIZATION] Failed to clean up S3 file: {e}")
                
            except ImportError as e:
                logger.error(f"Failed to import diarization dependencies: {e}")
                logger.error("Install with: uv pip install pyannote.audio torch torchaudio")
                logger.error("And set HF_TOKEN environment variable for pyannote models")
                # Clean up S3 file on error
                if s3_audio_filename and diarization_backend == "modal":
                    try:
                        await storage.delete_file(s3_audio_filename)
                    except:
                        pass
                sys.exit(1)
            except Exception as e:
                logger.error(f"Diarization failed: {e}")
                # Clean up S3 file on error
                if s3_audio_filename and diarization_backend == "modal":
                    try:
                        await storage.delete_file(s3_audio_filename)
                    except:
                        pass
                sys.exit(1)
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
        data = event.data
        
        # Debug log to trace event flow
        logger.debug(f"Event: processor={processor}, data_type={type(data).__name__}")
        
        # Ignore internal processors
        if processor in ("AudioChunkerProcessor", "AudioMergeProcessor", 
                        "AudioFileWriterProcessor", "TopicCollectorProcessor",
                        "BroadcastProcessor"):
            logger.debug(f"Filtering internal processor: {processor}")
            return
        
        # If diarization is enabled, skip the original topic events from the pipeline
        # The diarization processor will emit the same topics but with speaker info
        if processor == "TranscriptTopicDetectorProcessor" and args.enable_diarization:
            logger.debug(f"Skipping non-diarized topic event (will be emitted with speakers later)")
            return
        
        # Log all events
        logger.info(f"Event: {processor} - {type(data).__name__}")
        
        # Special logging for diarization events
        diarization_processors = ["AudioDiarizationAutoProcessor", "AudioDiarizationModalProcessor", "AudioDiarizationLocalProcessor"]
        logger.debug(f"[EVENT_CALLBACK] Checking if {processor} is in diarization processors: {processor in diarization_processors}")
        
        if processor in diarization_processors:
            logger.info(f"[DIARIZATION] EVENT DETECTED! Processor: {processor}")
            if hasattr(data, 'title'):
                logger.info(f"[DIARIZATION] Topic: {data.title[:50]}...")
            if hasattr(data, 'transcript') and data.transcript:
                has_speakers = any(hasattr(w, 'speaker') and w.speaker is not None 
                                 for w in (data.transcript.words or []))
                logger.info(f"[DIARIZATION] Has speaker info: {has_speakers}")
        
        # Write to output
        if output_fd:
            output_fd.write(event.model_dump_json())
            output_fd.write("\n")
            output_fd.flush()

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