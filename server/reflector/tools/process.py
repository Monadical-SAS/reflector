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

from reflector.db import get_database
from reflector.db.transcripts import SourceKind, transcripts_controller
from reflector.pipelines.main_live_pipeline import PipelineMainLive
import av

async def process_file_pipeline(
    filename: str,
    event_callback,
    source_language="en",
    target_language="en",
    output_fd=None,
):
    """Process audio/video file using the optimized file pipeline"""


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

        class PipelineMainLiveWithEvents(PipelineMainLive):
            def __init__(self, *args, event_callback=None, **kwargs):
                super().__init__(*args, **kwargs)
                self.event_callback = event_callback

            async def create(self):
                pipeline = await super().create()
                if self.event_callback:
                    pipeline.on(self.event_callback)
                return pipeline

            async def on_ended(self):
                # Call parent's on_ended which triggers pipeline_post
                await super().on_ended()

        pipeline = PipelineMainLiveWithEvents(
            transcript_id=transcript.id,
            event_callback=event_callback
        )
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
        # The issue is that pipeline.join() hangs because the runner loop is waiting for commands
        # We need to give it time to process the flush and set _ev_done
        # Then we can check if the pipeline has ended
        max_wait = 60
        waited = 0
        while waited < max_wait:
            await asyncio.sleep(1)
            waited += 1
            # Check if pipeline runner has ended
            if hasattr(pipeline, '_ev_done') and pipeline._ev_done.is_set():
                logger.info("Pipeline ended")
                break
            if hasattr(pipeline, 'status') and pipeline.status == 'ended':
                logger.info("Pipeline ended")
                break
            if waited % 10 == 0:
                logger.info(f"Waiting for pipeline to end... ({waited}s)")
        else:
            logger.warning(f"Pipeline did not end cleanly after {max_wait}s")

        # Manually trigger on_ended to start post-processing
        if hasattr(pipeline, 'on_ended'):
            logger.info("Triggering post-processing")
            await pipeline.on_ended()

        # Wait intelligently for processing to complete
        logger.info("Waiting for diarization and post-processing to complete...")

        async def wait_for_processing_complete(transcript_id: str, max_wait: int = 180):
            """Wait for transcript processing (including diarization) to complete."""
            poll_intervals = [2] * 10 + [5] * 10 + [10] * 11  # 2s×10, 5s×10, 10s×11 = 180s total
            total_waited = 0
            
            # Track progress metrics
            previous_topics = 0
            previous_words = 0
            previous_speakers = 0
            stalled_checks = 0
            max_stalled_checks = 10  # Fail after 10 consecutive checks with no progress (more tolerant)

            for interval in poll_intervals:
                await asyncio.sleep(interval)
                total_waited += interval

                transcript = await transcripts_controller.get_by_id(transcript_id)

                # Check for error status
                if transcript.status == "error":
                    logger.error(f"Processing failed after {total_waited}s")
                    return False

                # Count current metrics for progress tracking
                current_topics = len(transcript.topics) if transcript.topics else 0
                current_words = 0
                speakers = set()
                topics_with_speaker_0 = 0
                
                if transcript.topics:
                    for topic in transcript.topics:
                        topic_speakers = set()
                        if hasattr(topic, 'words') and topic.words:
                            current_words += len(topic.words)
                            for word in topic.words:
                                if hasattr(word, 'speaker'):
                                    speaker = word.speaker
                                    speakers.add(speaker)
                                    topic_speakers.add(speaker)
                        
                        # Count topics that only have speaker 0
                        if topic_speakers == {0}:
                            topics_with_speaker_0 += 1
                
                real_speakers = [s for s in speakers if s != 0]
                current_speakers = len(real_speakers)
                
                # Check for progress (any metric changing means progress)
                has_progress = (
                    current_topics > previous_topics or
                    current_words > previous_words or
                    current_speakers > previous_speakers
                )
                
                # Only check for stalls after initial activity (at least some content exists)
                # and only while status is "processing" and after reasonable time has passed
                if not has_progress and transcript.status == "processing" and current_topics > 0 and total_waited >= 60:
                    # No progress detected while still processing
                    stalled_checks += 1
                    if stalled_checks >= max_stalled_checks:
                        logger.error(
                            f"Processing stalled after {total_waited}s - no progress for {stalled_checks} checks. "
                            f"Topics: {current_topics}, Words: {current_words}, Speakers: {current_speakers}"
                        )
                        return False
                    elif total_waited % 10 == 0:
                        logger.warning(f"No progress detected, stall check {stalled_checks}/{max_stalled_checks}")
                else:
                    # Progress detected, status changed, or still initializing - reset stall counter
                    if has_progress and (previous_topics > 0 or current_topics > 0):
                        logger.debug(f"Progress detected: topics {previous_topics}->{current_topics}, "
                                   f"words {previous_words}->{current_words}, "
                                   f"speakers {previous_speakers}->{current_speakers}")
                    if stalled_checks > 0:
                        stalled_checks = 0
                        logger.debug("Stall counter reset")
                
                # Update previous values for next iteration
                previous_topics = current_topics
                previous_words = current_words
                previous_speakers = current_speakers
                
                # Check if processing is complete
                if transcript.status == "ended":
                    logger.info(f"Processing complete after {total_waited}s")
                    return True
                
                # Log progress every 10 seconds
                if total_waited % 10 == 0:
                    logger.info(
                        f"Waiting... ({total_waited}s, status: {transcript.status}, "
                        f"speakers: {current_speakers}, topics: {current_topics}, "
                        f"words: {current_words}, undiarized: {topics_with_speaker_0}, "
                        f"stalled_checks: {stalled_checks}/{max_stalled_checks})"
                    )

            logger.warning(f"Processing timeout after {total_waited}s")
            return True  # Return True to continue with what we have

        success = await wait_for_processing_complete(transcript.id)
        if not success:
            logger.error("Post-processing did not complete successfully")
            # Continue anyway to output what we have

        # Check if we need to re-run diarization for topics that were created late
        logger.info("Checking if all topics are diarized...")
        check_transcript = await transcripts_controller.get_by_id(transcript.id)
        
        if check_transcript.topics:
            undiarized_topics = 0
            for topic in check_transcript.topics:
                topic_speakers = set()
                if hasattr(topic, 'words') and topic.words:
                    for word in topic.words:
                        if hasattr(word, 'speaker'):
                            topic_speakers.add(word.speaker)
                if topic_speakers == {0}:
                    undiarized_topics += 1
            
            if undiarized_topics > 0:
                logger.info(f"Found {undiarized_topics} undiarized topics, triggering diarization again...")
                
                # Debug: Print full topics JSON
                import json
                topics_json = []
                for topic in check_transcript.topics:
                    topic_dict = {
                        'id': topic.id if hasattr(topic, 'id') else None,
                        'title': topic.title,
                        'summary': topic.summary,
                        'timestamp': topic.timestamp,
                        'transcript': topic.transcript,
                        'words': [
                            {
                                'text': w.text,
                                'start': w.start,
                                'end': w.end,
                                'speaker': w.speaker if hasattr(w, 'speaker') else None
                            } for w in topic.words
                        ] if hasattr(topic, 'words') and topic.words else []
                    }
                    topics_json.append(topic_dict)
                
                logger.info(f"TOPICS JSON: {json.dumps(topics_json, indent=2)}")
                
                # Import and trigger diarization task directly
                from reflector.pipelines.main_live_pipeline import task_pipeline_diarization
                result = task_pipeline_diarization.delay(transcript_id=transcript.id)
                logger.info(f"Re-diarization task started: {result.id}")
                
                # Wait for re-diarization to complete
                logger.info("Waiting for re-diarization to complete...")
                for i in range(15):  # Wait up to 75 seconds
                    await asyncio.sleep(5)
                    check_transcript = await transcripts_controller.get_by_id(transcript.id)
                    
                    # Check if diarization improved
                    new_undiarized = 0
                    for topic in check_transcript.topics:
                        topic_speakers = set()
                        if hasattr(topic, 'words') and topic.words:
                            for word in topic.words:
                                if hasattr(word, 'speaker'):
                                    topic_speakers.add(word.speaker)
                        if topic_speakers == {0}:
                            new_undiarized += 1
                    
                    if new_undiarized < undiarized_topics:
                        logger.info(f"Re-diarization progressing: {undiarized_topics} -> {new_undiarized} undiarized topics")
                        undiarized_topics = new_undiarized
                        if new_undiarized == 0:
                            logger.info("All topics now diarized!")
                            break
                    
                    if (i + 1) % 3 == 0:
                        logger.info(f"Still waiting for re-diarization... ({(i + 1) * 5}s)")
                else:
                    if undiarized_topics > 0:
                        logger.warning(f"Re-diarization timeout, {undiarized_topics} topics remain undiarized")

        # Fetch updated transcript with diarized results
        logger.info(f"Fetching diarized results from database transcript.id: {transcript.id}")
        final_transcript = await transcripts_controller.get_by_id(transcript.id)

        if output_fd:
            # Write diarized topics from database
            if final_transcript.topics:
                logger.info(f"Writing {len(final_transcript.topics)} diarized topics to output")
                for topic in final_transcript.topics:
                    # Convert topic to the expected format
                    topic_data = {
                        "title": topic.title,
                        "summary": topic.summary,
                        "timestamp": topic.timestamp,
                        "transcript": {
                            "text": topic.transcript,
                            "words": [
                                {
                                    "text": word.text,
                                    "start": word.start,
                                    "end": word.end,
                                    "speaker": word.speaker if hasattr(word, 'speaker') else 0
                                }
                                for word in topic.words
                            ] if hasattr(topic, 'words') and topic.words else []
                        }
                    }
                    
                    event = PipelineEvent(
                        processor="AudioDiarizationAutoProcessor",
                        uid=transcript.id,
                        data=topic_data
                    )
                    output_fd.write(event.model_dump_json())
                    output_fd.write("\n")
                    output_fd.flush()

                # Log speaker stats
                all_speakers = set()
                for topic in final_transcript.topics:
                    if hasattr(topic, 'transcript') and hasattr(topic.transcript, 'words'):
                        for word in topic.transcript.words:
                            if hasattr(word, 'speaker'):
                                all_speakers.add(word.speaker)
                # Filter out speaker 0 which indicates non-diarized content
                real_speakers = [s for s in all_speakers if s != 0]
                if real_speakers:
                    logger.info(f"Found {len(real_speakers)} unique speakers: {sorted(real_speakers)}")
                else:
                    logger.warning("Diarization may not have completed properly - only speaker 0 found")
                if 0 in all_speakers and real_speakers:
                    logger.info("Note: Some segments have speaker 0 (not diarized)")

        logger.info("File pipeline processing complete")

    finally:
        await database.disconnect()


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
            "AudioChunkerFramesProcessor",
            "AudioMergeProcessor",
            "AudioFileWriterProcessor",
            "TopicCollectorProcessor",
            "BroadcastProcessor",
        ):
            return

        # Log all events
        logger.info(f"Event: {processor} - {type(data).__name__}")

        # Don't write real-time events to output since we'll write diarized events later
        # This prevents duplicate events with different speaker IDs

    asyncio.run(
        process_file_pipeline(
            args.source,
            event_callback,
            source_language=args.source_language,
            target_language=args.target_language,
            output_fd=output_fd,
        )
    )


    if output_fd:
        output_fd.close()
        logger.info(f"Output written to {args.output}")
