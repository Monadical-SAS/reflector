#!/usr/bin/env python
"""
Simple test for diarization without Redis dependencies
"""

import asyncio
import json
from reflector.processors import (
    AudioChunkerProcessor,
    AudioMergeProcessor,
    AudioTranscriptAutoProcessor,
    AudioFileWriterProcessor,
    Pipeline,
)
import av

async def test_transcription():
    """Test basic transcription without Redis-dependent processors"""
    
    # Create temp file
    audio_temp_path = "/tmp/test_audio.wav"
    
    # Build simple pipeline
    processors = [
        AudioFileWriterProcessor(audio_temp_path),
        AudioChunkerProcessor(),
        AudioMergeProcessor(),
        AudioTranscriptAutoProcessor.as_threaded(),
    ]
    
    pipeline = Pipeline(*processors)
    pipeline.set_pref("audio:source_language", "en")
    pipeline.set_pref("audio:target_language", "en")
    
    # Track events
    events = []
    async def event_callback(event):
        if event.processor not in ("AudioChunkerProcessor", "AudioMergeProcessor", "AudioFileWriterProcessor"):
            events.append({
                "processor": event.processor,
                "data_type": type(event.data).__name__,
                "data": event.data.model_dump() if hasattr(event.data, 'model_dump') else str(event.data)
            })
            print(f"Event: {event.processor} - {type(event.data).__name__}")
    
    pipeline.on(event_callback)
    
    # Process audio
    filename = "/Users/firfi/work/clients/monadical/transcription-eval/files/40e7fc3c-6144-47a7-ba51-00591590046d-2025-07-22T14_56_47Z_cut.mp4"
    print(f"Opening {filename}")
    
    container = av.open(filename)
    try:
        print("Processing audio...")
        frame_count = 0
        for frame in container.decode(audio=0):
            await pipeline.push(frame)
            frame_count += 1
            if frame_count % 100 == 0:
                print(f"Processed {frame_count} frames...")
    finally:
        print("Flushing pipeline...")
        await pipeline.flush()
    
    print(f"\nProcessed {frame_count} total frames")
    print(f"Captured {len(events)} events")
    
    # Save events
    with open("test_transcription_output.json", "w") as f:
        json.dump(events, f, indent=2)
    
    print("\nSaved events to test_transcription_output.json")
    print(f"\nAudio saved to: {audio_temp_path}")
    
    # Show transcription results
    for event in events:
        if event["processor"] == "AudioTranscriptModalProcessor":
            transcript = event["data"]
            if "words" in transcript:
                print(f"\nTranscribed {len(transcript['words'])} words:")
                # Show first few words
                for word in transcript["words"][:10]:
                    print(f"  {word['text']} [{word['start']:.2f} - {word['end']:.2f}]")
                print("  ...")

if __name__ == "__main__":
    asyncio.run(test_transcription())