"""
Process audio file with diarization support
"""

import argparse
import asyncio
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

from reflector.db.transcripts import SourceKind, TranscriptTopic, transcripts_controller
from reflector.logger import logger
from reflector.pipelines.main_live_pipeline import pipeline_post, pipeline_process


def serialize_topics(topics: List[TranscriptTopic]) -> List[Dict[str, Any]]:
    """Convert TranscriptTopic objects to JSON-serializable dicts"""
    serialized = []
    for topic in topics:
        topic_dict = topic.model_dump()
        serialized.append(topic_dict)
    return serialized


def debug_print_speakers(serialized_topics: List[Dict[str, Any]]) -> None:
    """Print debug info about speakers found in topics"""
    all_speakers = set()
    for topic_dict in serialized_topics:
        for word in topic_dict.get("words", []):
            all_speakers.add(word.get("speaker", 0))

    print(
        f"Found {len(serialized_topics)} topics with speakers: {all_speakers}",
        file=sys.stderr,
    )


async def process_audio_file(
    source_path: str,
    source_language: str,
    target_language: str,
    output_path: str = None,
):
    """Process audio file with transcription and diarization"""

    user_id = None

    file_path = Path(source_path)

    transcript = await transcripts_controller.add(
        file_path.name,
        # note that the real file upload has SourceKind: LIVE for the reason of it's an error
        source_kind=SourceKind.FILE,
        source_language=source_language,
        target_language=target_language,
        user_id=user_id,
    )

    logger.info(
        f"Created empty transcript {transcript.id} for file {file_path.name} because technically we need an empty transcript before we start transcript"
    )

    # Copy the source file to transcript's data_path as upload.{extension}
    # This is a hardcoded undocumented convention - pipelines expect files as upload.*

    extension = file_path.suffix
    upload_path = transcript.data_path / f"upload{extension}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, upload_path)
    logger.info(f"Copied {source_path} to {upload_path}")

    # undocumented convention - we have to set status to "uploaded" for some reason
    await transcripts_controller.update(transcript, {"status": "uploaded"})

    print(f"Processing {file_path.name}...", file=sys.stderr)
    await pipeline_process(transcript_id=transcript.id)
    print(f"Processing complete for transcript {transcript.id}", file=sys.stderr)

    pre_final_transcript = await transcripts_controller.get_by_id(transcript.id)

    # assert documented behaviour: after process, the pipeline isn't ended. this is the reason of calling pipeline_post
    assert pre_final_transcript.status != "ended"

    # at this point, diarization is running but we have no access to it. run diarization in parallel - one will hopefully win after polling
    result = pipeline_post(transcript_id=transcript.id)

    # result.ready() blocks even without await; it mutates result also
    while not result.ready():
        print(f"Status: {result.state}")
        time.sleep(2)

    post_final_transcript = await transcripts_controller.get_by_id(transcript.id)

    assert post_final_transcript.status == "ended"

    topics = post_final_transcript.topics
    if not topics:
        raise RuntimeError(
            f"No topics found for transcript {transcript.id} after processing"
        )

    serialized_topics = serialize_topics(topics)

    if output_path:
        # Write to JSON file
        with open(output_path, "w") as f:
            for topic_dict in serialized_topics:
                json.dump(topic_dict, f)
                f.write("\n")
        print(f"Results written to {output_path}", file=sys.stderr)
    else:
        # Write to stdout as JSONL
        for topic_dict in serialized_topics:
            print(json.dumps(topic_dict))

    debug_print_speakers(serialized_topics)

    return transcript


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process audio files with speaker diarization"
    )
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    parser.add_argument(
        "--source-language", default="en", help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target-language", default="en", help="Target language code (default: en)"
    )
    parser.add_argument("--output", "-o", help="Output file (output.jsonl)")
    args = parser.parse_args()

    asyncio.run(
        process_audio_file(
            args.source, args.source_language, args.target_language, args.output
        )
    )
