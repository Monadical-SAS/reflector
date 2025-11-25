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
from typing import Any, Dict, List, Literal, Tuple
from urllib.parse import unquote, urlparse

from botocore.exceptions import BotoCoreError, ClientError, NoCredentialsError

from reflector.db.transcripts import SourceKind, TranscriptTopic, transcripts_controller
from reflector.logger import logger
from reflector.pipelines.main_file_pipeline import (
    task_pipeline_file_process as task_pipeline_file_process,
)
from reflector.pipelines.main_live_pipeline import pipeline_post as live_pipeline_post
from reflector.pipelines.main_live_pipeline import (
    pipeline_process as live_pipeline_process,
)
from reflector.storage import Storage


def validate_s3_bucket_name(bucket: str) -> None:
    if not bucket:
        raise ValueError("Bucket name cannot be empty")
    if len(bucket) > 255:  # Absolute max for any region
        raise ValueError(f"Bucket name too long: {len(bucket)} characters (max 255)")


def validate_s3_key(key: str) -> None:
    if not key:
        raise ValueError("S3 key cannot be empty")
    if len(key) > 1024:
        raise ValueError(f"S3 key too long: {len(key)} characters (max 1024)")


def parse_s3_url(url: str) -> Tuple[str, str]:
    parsed = urlparse(url)

    if parsed.scheme == "s3":
        bucket = parsed.netloc
        key = parsed.path.lstrip("/")
        if parsed.fragment:
            logger.debug(
                "URL fragment ignored (not part of S3 key)",
                url=url,
                fragment=parsed.fragment,
            )
        if not bucket or not key:
            raise ValueError(f"Invalid S3 URL: {url} (missing bucket or key)")
        bucket = unquote(bucket)
        key = unquote(key)
        validate_s3_bucket_name(bucket)
        validate_s3_key(key)
        return bucket, key

    elif parsed.scheme in ("http", "https"):
        if ".s3." in parsed.netloc or parsed.netloc.endswith(".s3.amazonaws.com"):
            bucket = parsed.netloc.split(".")[0]
            key = parsed.path.lstrip("/")
            if parsed.fragment:
                logger.debug("URL fragment ignored", url=url, fragment=parsed.fragment)
            if not bucket or not key:
                raise ValueError(f"Invalid S3 URL: {url} (missing bucket or key)")
            bucket = unquote(bucket)
            key = unquote(key)
            validate_s3_bucket_name(bucket)
            validate_s3_key(key)
            return bucket, key

        elif parsed.netloc.startswith("s3.") and "amazonaws.com" in parsed.netloc:
            path_parts = parsed.path.lstrip("/").split("/", 1)
            if len(path_parts) != 2:
                raise ValueError(f"Invalid S3 URL: {url} (missing bucket or key)")
            bucket, key = path_parts
            if parsed.fragment:
                logger.debug("URL fragment ignored", url=url, fragment=parsed.fragment)
            bucket = unquote(bucket)
            key = unquote(key)
            validate_s3_bucket_name(bucket)
            validate_s3_key(key)
            return bucket, key

        else:
            raise ValueError(f"Invalid S3 URL format: {url} (not recognized as S3 URL)")

    else:
        raise ValueError(f"Invalid S3 URL scheme: {url} (must be s3:// or https://)")


async def validate_s3_objects(
    storage: Storage, bucket_keys: List[Tuple[str, str]]
) -> None:
    async with storage.session.client("s3") as client:

        async def check_object(bucket: str, key: str) -> None:
            try:
                await client.head_object(Bucket=bucket, Key=key)
            except ClientError as e:
                error_code = e.response["Error"]["Code"]
                if error_code in ("404", "NoSuchKey"):
                    raise ValueError(f"S3 object not found: s3://{bucket}/{key}") from e
                elif error_code in ("403", "Forbidden", "AccessDenied"):
                    raise ValueError(
                        f"Access denied for S3 object: s3://{bucket}/{key}. "
                        f"Check AWS credentials and permissions"
                    ) from e
                else:
                    raise ValueError(
                        f"S3 error {error_code} for s3://{bucket}/{key}: "
                        f"{e.response['Error'].get('Message', 'Unknown error')}"
                    ) from e
            except NoCredentialsError as e:
                raise ValueError(
                    "AWS credentials not configured. Set AWS_ACCESS_KEY_ID and "
                    "AWS_SECRET_ACCESS_KEY environment variables"
                ) from e
            except BotoCoreError as e:
                raise ValueError(
                    f"AWS service error for s3://{bucket}/{key}: {str(e)}"
                ) from e
            except Exception as e:
                raise ValueError(
                    f"Unexpected error validating s3://{bucket}/{key}: {str(e)}"
                ) from e

        await asyncio.gather(
            *(check_object(bucket, key) for bucket, key in bucket_keys)
        )


def serialize_topics(topics: List[TranscriptTopic]) -> List[Dict[str, Any]]:
    serialized = []
    for topic in topics:
        topic_dict = topic.model_dump()
        serialized.append(topic_dict)
    return serialized


def debug_print_speakers(serialized_topics: List[Dict[str, Any]]) -> None:
    all_speakers = set()
    for topic_dict in serialized_topics:
        for word in topic_dict.get("words", []):
            all_speakers.add(word.get("speaker", 0))

    print(
        f"Found {len(serialized_topics)} topics with speakers: {all_speakers}",
        file=sys.stderr,
    )


TranscriptId = str


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

    logger.info(f"Created transcript {transcript.id} for {file_path.name}")

    # pipelines expect files as upload.*

    extension = file_path.suffix
    upload_path = transcript.data_path / f"upload{extension}"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_path, upload_path)
    logger.info(f"Copied {source_path} to {upload_path}")

    # pipelines expect entity status "uploaded"
    await transcripts_controller.update(transcript, {"status": "uploaded"})

    return transcript.id


async def extract_result_from_entry(
    transcript_id: TranscriptId, output_path: str
) -> None:
    post_final_transcript = await transcripts_controller.get_by_id(transcript_id)

    # assert post_final_transcript.status == "ended"
    # File pipeline doesn't set status to "ended", only live pipeline does https://github.com/Monadical-SAS/reflector/issues/582
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
    parser.add_argument(
        "source",
        help="Source file (mp3, wav, mp4...) or comma-separated S3 URLs with --multitrack",
    )
    parser.add_argument(
        "--pipeline",
        choices=["live", "file"],
        help="Pipeline type to use for processing (live: streaming/incremental, file: batch/parallel)",
    )
    parser.add_argument(
        "--multitrack",
        action="store_true",
        help="Process multiple audio tracks from comma-separated S3 URLs",
    )
    parser.add_argument(
        "--source-language", default="en", help="Source language code (default: en)"
    )
    parser.add_argument(
        "--target-language", default="en", help="Target language code (default: en)"
    )
    parser.add_argument("--output", "-o", help="Output file (output.jsonl)")
    args = parser.parse_args()

    if args.multitrack:
        if not args.source:
            parser.error("Source URLs required for multitrack processing")

        s3_urls = [url.strip() for url in args.source.split(",") if url.strip()]

        if not s3_urls:
            parser.error("At least one S3 URL required for multitrack processing")

        from reflector.tools.cli_multitrack import process_multitrack_cli

        asyncio.run(
            process_multitrack_cli(
                s3_urls,
                args.source_language,
                args.target_language,
                args.output,
            )
        )
    else:
        if not args.pipeline:
            parser.error("--pipeline is required for single-track processing")

        if "," in args.source:
            parser.error(
                "Multiple files detected. Use --multitrack flag for multitrack processing"
            )

        asyncio.run(
            process(
                args.source,
                args.source_language,
                args.target_language,
                args.pipeline,
                args.output,
            )
        )
