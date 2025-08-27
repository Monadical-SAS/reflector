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
from typing import Any, Dict, List, Literal

from reflector.db.transcripts import SourceKind, TranscriptTopic, transcripts_controller
from reflector.logger import logger
from reflector.pipelines.main_file_pipeline import (
    task_pipeline_file_process as task_pipeline_file_process,
)
from reflector.pipelines.main_live_pipeline import pipeline_post as live_pipeline_post
from reflector.pipelines.main_live_pipeline import (
    pipeline_process as live_pipeline_process,
)


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


TranscriptId = str


# common interface for every flow: it needs an Entry in db with specific ceremony (file path + status + actual file in file system)
# ideally we want to get rid of it at some point
async def prepare_entry(
    source_path: str,
    source_language: str,
    target_language: str,
) -> TranscriptId:
    file_path = Path(source_path)

    transcript = await transcripts_controller.add(
        file_path.name,
        # note that the real file upload has SourceKind: LIVE for the reason of it's an error
        source_kind=SourceKind.FILE,
        source_language=source_language,
        target_language=target_language,
        user_id=None,
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

    return transcript.id


# same, a part of common ceremony with communication through "transcript" table. to be removed
async def extract_result_from_entry(
    transcript_id: TranscriptId, output_path: str
) -> None:
    post_final_transcript = await transcripts_controller.get_by_id(transcript_id)

    # assert post_final_transcript.status == "ended"
    # File pipeline doesn't set status to "ended", only live pipeline does
    topics = post_final_transcript.topics
    if not topics:
        raise RuntimeError(
            f"No topics found for transcript {transcript_id} after processing"
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


async def process_live_pipeline(
    transcript_id: TranscriptId,
):
    """Process transcript_id with transcription and diarization"""

    print(f"Processing transcript_id {transcript_id}...", file=sys.stderr)
    await live_pipeline_process(transcript_id=transcript_id)
    print(f"Processing complete for transcript {transcript_id}", file=sys.stderr)

    pre_final_transcript = await transcripts_controller.get_by_id(transcript_id)

    # assert documented behaviour: after process, the pipeline isn't ended. this is the reason of calling pipeline_post
    assert pre_final_transcript.status != "ended"

    # at this point, diarization is running but we have no access to it. run diarization in parallel - one will hopefully win after polling
    result = live_pipeline_post(transcript_id=transcript_id)

    # result.ready() blocks even without await; it mutates result also
    while not result.ready():
        print(f"Status: {result.state}")
        time.sleep(2)


async def process_file_pipeline(
    transcript_id: TranscriptId,
):
    """Process audio/video file using the optimized file pipeline"""

    # task_pipeline_file_process is a Celery task, need to use .delay() for async execution
    result = task_pipeline_file_process.delay(transcript_id=transcript_id)

    # Wait for the Celery task to complete
    while not result.ready():
        print(f"File pipeline status: {result.state}", file=sys.stderr)
        time.sleep(2)

    logger.info("File pipeline processing complete")


async def process(
    source_path: str,
    source_language: str,
    target_language: str,
    pipeline: Literal["live", "file"],
    output_path: str = None,
):
    from reflector.db import get_database

    database = get_database()
    # db connect is a part of ceremony
    await database.connect()

    try:
        transcript_id = await prepare_entry(
            source_path,
            source_language,
            target_language,
        )

        pipeline_handlers = {
            "live": process_live_pipeline,
            "file": process_file_pipeline,
        }

        handler = pipeline_handlers.get(pipeline)
        if not handler:
            raise ValueError(f"Unknown pipeline type: {pipeline}")

        await handler(transcript_id)

        await extract_result_from_entry(transcript_id, output_path)
    finally:
        await database.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Process audio files with speaker diarization"
    )
    parser.add_argument("source", help="Source file (mp3, wav, mp4...)")
    parser.add_argument(
        "--pipeline",
        required=True,
        choices=["live", "file"],
        help="Pipeline type to use for processing (live: streaming/incremental, file: batch/parallel)",
    )
    parser.add_argument(
        "--source-language", default="en", help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target-language", default="en", help="Target language code (default: en)"
    )
    parser.add_argument("--output", "-o", help="Output file (output.jsonl)")
    args = parser.parse_args()

    asyncio.run(
        process(
            args.source,
            args.source_language,
            args.target_language,
            args.pipeline,
            args.output,
        )
    )
