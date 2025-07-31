#!/usr/bin/env python3
"""
@vibe-generated
Test script for the diarization CLI tool
=========================================

This script helps test the diarization functionality with sample audio files.
"""

import asyncio
import sys
from pathlib import Path

from reflector.logger import logger


async def test_diarization(audio_file: str):
    """Test the diarization functionality"""

    # Import the processing function
    from process_with_diarization import process_audio_file_with_diarization

    # Collect events
    events = []

    async def event_callback(event):
        events.append({"processor": event.processor, "data": event.data})
        logger.info(f"Event from {event.processor}")

    # Process the audio file
    logger.info(f"Processing audio file: {audio_file}")

    try:
        await process_audio_file_with_diarization(
            audio_file,
            event_callback,
            only_transcript=False,
            source_language="en",
            target_language="en",
            enable_diarization=True,
            diarization_backend="modal",
        )

        # Analyze results
        logger.info(f"Processing complete. Received {len(events)} events")

        # Look for diarization results
        diarized_topics = []
        for event in events:
            if "TitleSummary" in event["processor"]:
                # Check if words have speaker information
                if hasattr(event["data"], "transcript") and event["data"].transcript:
                    words = event["data"].transcript.words
                    if words and hasattr(words[0], "speaker"):
                        speakers = set(
                            w.speaker for w in words if hasattr(w, "speaker")
                        )
                        logger.info(
                            f"Found {len(speakers)} speakers in topic: {event['data'].title}"
                        )
                        diarized_topics.append(event["data"])

        if diarized_topics:
            logger.info(f"Successfully diarized {len(diarized_topics)} topics")

            # Print sample output
            sample_topic = diarized_topics[0]
            logger.info("Sample diarized output:")
            for i, word in enumerate(sample_topic.transcript.words[:10]):
                logger.info(f"  Word {i}: '{word.text}' - Speaker {word.speaker}")
        else:
            logger.warning("No diarization results found in output")

        return events

    except Exception as e:
        logger.error(f"Error during processing: {e}")
        raise


def main():
    if len(sys.argv) < 2:
        print("Usage: python test_diarization.py <audio_file>")
        sys.exit(1)

    audio_file = sys.argv[1]
    if not Path(audio_file).exists():
        print(f"Error: Audio file '{audio_file}' not found")
        sys.exit(1)

    # Run the test
    asyncio.run(test_diarization(audio_file))


if __name__ == "__main__":
    main()
