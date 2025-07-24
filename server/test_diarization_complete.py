#!/usr/bin/env python
"""
Complete test for diarization with local backend
"""

import asyncio
import json
import os
from pathlib import Path
from reflector.processors import AudioDiarizationAutoProcessor
from reflector.processors.types import AudioDiarizationInput, TitleSummaryWithId, Transcript, Word

# Import local backend to register it
import reflector.processors.audio_diarization_local

async def test_diarization():
    """Test diarization with the transcription output"""
    
    # Load transcription output
    with open("test_transcription_output.json", "r") as f:
        events = json.load(f)
    
    # Extract transcript data and create topics
    topics = []
    topic_id = 0
    
    for event in events:
        if event["processor"] == "AudioTranscriptModalProcessor":
            topic_id += 1
            transcript_data = event["data"]
            
            # Create words from transcript data
            words = []
            for w in transcript_data.get("words", []):
                words.append(Word(
                    text=w["text"],
                    start=w["start"],
                    end=w["end"],
                    speaker=w.get("speaker", 0)
                ))
            
            # Create topic
            topic = TitleSummaryWithId(
                id=str(topic_id),
                title=f"Topic {topic_id}",
                summary=transcript_data.get("text", ""),
                timestamp=words[0].start if words else 0.0,
                duration=words[-1].end - words[0].start if words else 0.0,
                transcript=Transcript(words=words)
            )
            topics.append(topic)
    
    print(f"Created {len(topics)} topics from transcription")
    
    # Set up HuggingFace token if available
    hf_token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not hf_token:
        print("\nWARNING: No HuggingFace token found. Some models require authentication.")
        print("Set HF_TOKEN or HUGGINGFACE_TOKEN environment variable.")
        return
    
    # Create diarization input
    audio_path = "/tmp/test_audio.wav"
    if not Path(audio_path).exists():
        print(f"\nERROR: Audio file not found at {audio_path}")
        print("Run test_diarization_simple.py first to generate the audio file")
        return
    
    diarization_input = AudioDiarizationInput(
        audio_url=audio_path,
        topics=topics
    )
    
    # Create diarization processor
    print("\nInitializing diarization processor...")
    diarization_processor = AudioDiarizationAutoProcessor(name="local")
    
    # Track events
    diarization_events = []
    async def event_callback(event):
        diarization_events.append({
            "processor": event.processor,
            "data_type": type(event.data).__name__,
        })
        print(f"Diarization event: {event.processor} - {type(event.data).__name__}")
    
    diarization_processor.on(event_callback)
    
    # Run diarization
    print("\nRunning diarization...")
    try:
        await diarization_processor.push(diarization_input)
        await diarization_processor.flush()
        print("Diarization complete!")
    except Exception as e:
        print(f"Diarization failed: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # Check speaker assignments
    print("\nChecking speaker assignments...")
    speakers_found = set()
    total_words = 0
    
    for topic in topics:
        if topic.transcript and topic.transcript.words:
            for word in topic.transcript.words:
                total_words += 1
                if hasattr(word, 'speaker') and word.speaker is not None:
                    speakers_found.add(word.speaker)
    
    print(f"\nSpeakers found: {sorted(speakers_found)}")
    print(f"Total words processed: {total_words}")
    
    # Show sample of speaker assignments
    print("\nSample speaker assignments:")
    sample_count = 0
    for topic in topics[:3]:  # First 3 topics
        if topic.transcript and topic.transcript.words:
            print(f"\nTopic {topic.id}:")
            for word in topic.transcript.words[:10]:  # First 10 words
                print(f"  Speaker {word.speaker}: {word.text} [{word.start:.2f}-{word.end:.2f}]")
                sample_count += 1
            if len(topic.transcript.words) > 10:
                print("  ...")
    
    # Save diarized output
    output_data = {
        "topics": [topic.model_dump() for topic in topics],
        "speakers_found": sorted(speakers_found),
        "total_words": total_words
    }
    
    with open("test_diarization_output.json", "w") as f:
        json.dump(output_data, f, indent=2)
    
    print(f"\nDiarization results saved to test_diarization_output.json")

if __name__ == "__main__":
    asyncio.run(test_diarization())