#!/usr/bin/env python
"""
Test script to trigger multitrack recording processing with ffmpeg padding fix
This version loads tracks from local filesystem instead of S3
"""

import asyncio
import os

from reflector.pipelines.main_multitrack_pipeline import PipelineMainMultitrack


async def test_processing():
    """Manually trigger multitrack processing for the test recording"""

    # Initialize database connection
    from reflector.db import get_database

    db = get_database()
    await db.connect()

    try:
        # Create a new transcript ID
        import uuid

        transcript_id = str(uuid.uuid4())

        # Create transcript directly with SQL
        from reflector.db.transcripts import (
            Transcript,
            transcripts,
            transcripts_controller,
        )

        pipeline = PipelineMainMultitrack(transcript_id=transcript_id)

        # Create transcript model
        transcript = Transcript(
            id=transcript_id,
            name="FFMPEG Test - Daily Multitrack Recording",
            source_kind="file",
            source_language="en",
            target_language="en",
            status="idle",
            events=[],
            title="",
        )
        # Insert into database
        query = transcripts.insert().values(**transcript.model_dump())
        await db.execute(query)
        print(f"Created transcript: {transcript_id}")

        # Read track files from local filesystem (in the container they'll be at /app/)
        tracks_dir = "/app"
        track_files = [
            "1760988935484-52f7f48b-fbab-431f-9a50-87b9abfc8255-cam-audio-1760988935922.webm",
            "1760988935484-a37c35e3-6f8e-4274-a482-e9d0f102a732-cam-audio-1760988943823.webm",
        ]

        # Read track data
        track_datas = []
        for track_file in track_files:
            file_path = os.path.join(tracks_dir, track_file)
            if os.path.exists(file_path):
                with open(file_path, "rb") as f:
                    track_datas.append(f.read())
                print(f"Loaded track: {track_file} ({len(track_datas[-1])} bytes)")
            else:
                print(f"Track file not found: {file_path}")
                track_datas.append(b"")

        # Process the tracks using the pipeline
        print(f"\nProcessing multitrack recording with ffmpeg padding...")
        print(f"Track 0: ...935922.webm (expected to start at ~2s)")
        print(f"Track 1: ...943823.webm (expected to start at ~51s)")

        # Call the process method directly with track data
        # We'll need to mock S3 operations and directly work with the data

        # Save tracks to temporary files and process them

        try:
            await pipeline.set_status(transcript_id, "processing")

            # Create a mock bucket and keys setup
            bucket_name = "test-bucket"
            track_keys = ["track0.webm", "track1.webm"]

            # Mock S3 client to return our local data
            from unittest.mock import MagicMock, patch

            mock_s3 = MagicMock()

            def mock_get_object(Bucket, Key):
                idx = 0 if "track0" in Key else 1
                return {"Body": MagicMock(read=lambda: track_datas[idx])}

            mock_s3.get_object = mock_get_object

            # Patch boto3.client to return our mock
            with patch("boto3.client", return_value=mock_s3):
                await pipeline.process(bucket_name, track_keys)

            print(f"Processing complete!")
        except Exception as e:
            await pipeline.set_status(transcript_id, "error")
            print(f"Error during processing: {e}")
            import traceback

            traceback.print_exc()
            raise

        # Check the results
        final_transcript = await transcripts_controller.get(transcript_id)
        print(f"\nTranscript status: {final_transcript.status}")
        print(f"Transcript title: {final_transcript.title}")

        # Extract timeline from events
        if final_transcript.events:
            for event in final_transcript.events:
                if event.get("event") == "TRANSCRIPT":
                    text = event.get("data", {}).get("text", "")
                    # Show first 500 chars to check if speakers are properly separated
                    print(f"\nTranscript text (first 500 chars):")
                    print(text[:500])

                    # Show last 500 chars too to see if second speaker is at the end
                    print(f"\nTranscript text (last 500 chars):")
                    print(text[-500:])

                    # Count words per speaker
                    words = text.split()
                    print(f"\nTotal words in transcript: {len(words)}")

                    # Check if text has proper speaker separation
                    # Expected: First ~45% from speaker 0, then ~35% from speaker 1, then ~20% from speaker 0
                    first_third = " ".join(words[: len(words) // 3])
                    middle_third = " ".join(
                        words[len(words) // 3 : 2 * len(words) // 3]
                    )
                    last_third = " ".join(words[2 * len(words) // 3 :])

                    print(f"\nFirst third preview: {first_third[:100]}...")
                    print(f"Middle third preview: {middle_third[:100]}...")
                    print(f"Last third preview: {last_third[:100]}...")
                    break

        return transcript_id
    finally:
        await db.disconnect()


if __name__ == "__main__":
    transcript_id = asyncio.run(test_processing())
    print(f"\n✅ Test complete! Transcript ID: {transcript_id}")
    print(f"\nExpected timeline:")
    print(f"  Speaker 0: ~2s to ~49s (first participant speaks)")
    print(f"  Speaker 1: ~51s to ~70s (second participant speaks)")
    print(f"  Speaker 0: ~73s to end (first participant speaks again)")
    print(
        f"\nIf the text shows proper chronological order (not interleaved), the fix worked!"
    )
