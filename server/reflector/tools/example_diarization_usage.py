#!/usr/bin/env python3
"""
Example: Direct usage of diarization components
===============================================

This example shows how to use the diarization components directly
without the full CLI pipeline, useful for integration into other tools.
"""

import asyncio
from pathlib import Path

# Add the parent directory to the path to import reflector modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from reflector.processors.types import (
    AudioDiarizationInput,
    TitleSummaryWithId,
    Transcript,
    Word,
)
from reflector.logger import logger


async def diarize_with_existing_transcript(audio_file: str, transcript_data: dict):
    """
    Example of how to add diarization to an existing transcript
    
    Args:
        audio_file: Path to the audio file
        transcript_data: Dictionary containing transcript with words and timestamps
    """
    
    # Import and register the local diarization backend
    import reflector.processors.audio_diarization_local
    from reflector.processors import AudioDiarizationAutoProcessor
    
    # Create topic from transcript data
    topic = TitleSummaryWithId(
        id="1",
        title=transcript_data.get("title", "Untitled"),
        summary=transcript_data.get("summary", ""),
        timestamp=0.0,
        duration=transcript_data.get("duration", 0.0),
        transcript=Transcript(
            words=[
                Word(
                    text=w["text"],
                    start=w["start"],
                    end=w["end"],
                    speaker=0  # Default speaker, will be updated by diarization
                )
                for w in transcript_data["words"]
            ]
        )
    )
    
    # Create diarization processor
    diarizer = AudioDiarizationAutoProcessor(name="local")
    
    # Create diarization input
    diarization_input = AudioDiarizationInput(
        audio_url=str(Path(audio_file).absolute()),
        topics=[topic]
    )
    
    # Collect output
    output_topics = []
    
    async def on_output(data):
        output_topics.append(data)
    
    diarizer.on(on_output)
    
    # Run diarization
    logger.info("Starting diarization...")
    await diarizer.push(diarization_input)
    await diarizer.flush()
    
    # The diarization processor modifies the words in-place
    # Let's examine the results
    if output_topics:
        diarized_topic = output_topics[0]
        
        # Count speakers
        speakers = set()
        for word in diarized_topic.transcript.words:
            speakers.add(word.speaker)
        
        logger.info(f"Diarization complete. Found {len(speakers)} speakers.")
        
        # Show sample output
        logger.info("Sample diarized transcript:")
        current_speaker = None
        for word in diarized_topic.transcript.words[:20]:  # First 20 words
            if word.speaker != current_speaker:
                current_speaker = word.speaker
                print(f"\n[Speaker {current_speaker}]: ", end="")
            print(f"{word.text} ", end="")
        print("\n")
        
        return diarized_topic
    
    return None


async def main():
    # Example transcript data (you would get this from your transcription service)
    sample_transcript = {
        "title": "Sample Conversation",
        "summary": "A conversation between two people",
        "duration": 10.0,
        "words": [
            {"text": "Hello,", "start": 0.0, "end": 0.5},
            {"text": "how", "start": 0.5, "end": 0.7},
            {"text": "are", "start": 0.7, "end": 0.9},
            {"text": "you?", "start": 0.9, "end": 1.2},
            {"text": "I'm", "start": 2.0, "end": 2.2},
            {"text": "doing", "start": 2.2, "end": 2.5},
            {"text": "great,", "start": 2.5, "end": 2.9},
            {"text": "thanks!", "start": 2.9, "end": 3.3},
            {"text": "That's", "start": 4.0, "end": 4.3},
            {"text": "wonderful", "start": 4.3, "end": 4.8},
            {"text": "to", "start": 4.8, "end": 4.9},
            {"text": "hear.", "start": 4.9, "end": 5.2},
        ]
    }
    
    # You would replace this with your actual audio file
    audio_file = "path/to/your/audio.wav"
    
    # Check if audio file exists
    if not Path(audio_file).exists():
        logger.error(f"Audio file not found: {audio_file}")
        logger.info("Please update the 'audio_file' variable with a valid audio file path")
        return
    
    # Run diarization
    result = await diarize_with_existing_transcript(audio_file, sample_transcript)
    
    if result:
        logger.info("Diarization successful!")
        
        # You can now use the diarized transcript
        # For example, save it to a file or send to another service
        import json
        output_data = {
            "title": result.title,
            "summary": result.summary,
            "words": [
                {
                    "text": w.text,
                    "start": w.start,
                    "end": w.end,
                    "speaker": w.speaker
                }
                for w in result.transcript.words
            ]
        }
        
        print("\nFull diarized output:")
        print(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    # Make sure to set HF_TOKEN environment variable if using pyannote models
    import os
    if not os.environ.get("HF_TOKEN") and not os.environ.get("HUGGINGFACE_TOKEN"):
        logger.warning(
            "No HuggingFace token found. You may need to set HF_TOKEN or HUGGINGFACE_TOKEN "
            "environment variable for pyannote models."
        )
    
    asyncio.run(main())