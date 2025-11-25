"""
Process transcript by ID - auto-detects multitrack vs file pipeline.

Usage:
    uv run -m reflector.tools.process_transcript <transcript_id>

    # Or via docker:
    docker compose exec server uv run -m reflector.tools.process_transcript <transcript_id>
"""

import argparse
import asyncio
import sys
import time
from typing import Callable

from celery.result import AsyncResult

from reflector.db.transcripts import Transcript, transcripts_controller
from reflector.services.transcript_process import (
    FileProcessingConfig,
    MultitrackProcessingConfig,
    PrepareResult,
    ProcessError,
    ValidationError,
    ValidationResult,
    dispatch_transcript_processing,
    prepare_transcript_processing,
    validate_transcript_for_processing,
)


async def process_transcript_inner(
    transcript: Transcript,
    on_validation: Callable[[ValidationResult], None],
    on_preprocess: Callable[[PrepareResult], None],
) -> AsyncResult:
    validation = await validate_transcript_for_processing(transcript)
    on_validation(validation)
    config = await prepare_transcript_processing(validation)
    on_preprocess(config)
    return dispatch_transcript_processing(config)


async def process_transcript(transcript_id: str, sync: bool = False) -> None:
    """
    Process a transcript by ID, auto-detecting multitrack vs file pipeline.

    Args:
        transcript_id: The transcript UUID
        sync: If True, wait for task completion. If False, dispatch and exit.
    """
    from reflector.db import get_database

    database = get_database()
    await database.connect()

    try:
        transcript = await transcripts_controller.get_by_id(transcript_id)
        if not transcript:
            print(f"Error: Transcript {transcript_id} not found", file=sys.stderr)
            sys.exit(1)

        print(f"Found transcript: {transcript.title or transcript_id}", file=sys.stderr)
        print(f"  Status: {transcript.status}", file=sys.stderr)
        print(f"  Recording ID: {transcript.recording_id or 'None'}", file=sys.stderr)

        def on_validation(validation: ValidationResult) -> None:
            if isinstance(validation, ValidationError):
                print(f"Error: {validation.detail}", file=sys.stderr)
                sys.exit(1)

        def on_preprocess(config: PrepareResult) -> None:
            if isinstance(config, ProcessError):
                print(f"Error: {config.detail}", file=sys.stderr)
                sys.exit(1)
            elif isinstance(config, MultitrackProcessingConfig):
                print(f"Dispatching multitrack pipeline", file=sys.stderr)
                print(f"  Bucket: {config.bucket_name}", file=sys.stderr)
                print(f"  Tracks: {len(config.track_keys)}", file=sys.stderr)
            elif isinstance(config, FileProcessingConfig):
                print(f"Dispatching file pipeline", file=sys.stderr)

        result = await process_transcript_inner(
            transcript, on_validation=on_validation, on_preprocess=on_preprocess
        )

        if sync:
            print("Waiting for task completion...", file=sys.stderr)
            while not result.ready():
                print(f"  Status: {result.state}", file=sys.stderr)
                time.sleep(5)

            if result.successful():
                print("Task completed successfully", file=sys.stderr)
            else:
                print(f"Task failed: {result.result}", file=sys.stderr)
                sys.exit(1)
        else:
            print(
                "Task dispatched (use --sync to wait for completion)", file=sys.stderr
            )

    finally:
        await database.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Process transcript by ID - auto-detects multitrack vs file pipeline"
    )
    parser.add_argument(
        "transcript_id",
        help="Transcript UUID to process",
    )
    parser.add_argument(
        "--sync",
        action="store_true",
        help="Wait for task completion instead of just dispatching",
    )

    args = parser.parse_args()
    asyncio.run(process_transcript(args.transcript_id, sync=args.sync))


if __name__ == "__main__":
    main()
