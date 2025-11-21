"""CLI-specific orchestration for multitrack processing.

This module handles all CLI concerns like progress printing, status updates,
and output formatting. It uses the multitrack service for business logic.
"""

import sys
from typing import List, Optional

import structlog

from reflector.db import get_database
from reflector.services.multitrack import (
    StatusCallback,
    process_multitrack,
)
from reflector.storage import get_transcripts_storage
from reflector.tools.process import (
    extract_result_from_entry,
    parse_s3_url,
    validate_s3_objects,
)

logger = structlog.get_logger(__name__)


def print_progress(message: str) -> None:
    """Print progress message to stderr for CLI visibility."""
    print(f"{message}", file=sys.stderr)


def create_status_callback() -> StatusCallback:
    """Create callback for task status updates during polling."""

    def callback(state: str, elapsed_seconds: int) -> None:
        print_progress(
            f"Multitrack pipeline status: {state} (elapsed: {elapsed_seconds}s)"
        )

    return callback


async def process_multitrack_cli(
    s3_urls: List[str],
    source_language: str,
    target_language: str,
    output_path: Optional[str] = None,
) -> None:
    """Process multitrack recording from S3 URLs with CLI output.

    This is the main entry point for CLI-based multitrack processing.
    It handles all CLI-specific concerns like progress printing and
    error formatting for terminal output.

    Args:
        s3_urls: List of S3 URLs for audio tracks
        source_language: Source language code
        target_language: Target language code
        output_path: Optional output file path for JSONL

    Raises:
        ValueError: Invalid URLs or validation failures
        TimeoutError: If processing exceeds timeout
        RuntimeError: If pipeline processing fails
    """
    # Validate arguments
    if not s3_urls:
        raise ValueError("At least one track required for multitrack processing")

    # Parse and validate S3 URLs
    bucket_keys = []
    for url in s3_urls:
        try:
            bucket, key = parse_s3_url(url)
            bucket_keys.append((bucket, key))
        except ValueError as e:
            raise ValueError(f"Invalid S3 URL '{url}': {e}") from e

    # Ensure all tracks are in the same bucket
    buckets = set(bucket for bucket, _ in bucket_keys)
    if len(buckets) > 1:
        raise ValueError(
            f"All tracks must be in the same S3 bucket. "
            f"Found {len(buckets)} different buckets: {sorted(buckets)}. "
            f"Please upload all files to a single bucket."
        )

    primary_bucket = bucket_keys[0][0]
    track_keys = [key for _, key in bucket_keys]

    print_progress(
        f"Starting multitrack CLI processing: "
        f"bucket={primary_bucket}, num_tracks={len(track_keys)}, "
        f"source_language={source_language}, target_language={target_language}"
    )

    # Validate S3 objects exist
    storage = get_transcripts_storage()
    await validate_s3_objects(storage, bucket_keys)
    print_progress(f"S3 validation complete: {len(bucket_keys)} objects verified")

    # Process using service layer
    result = await process_multitrack(
        bucket_name=primary_bucket,
        track_keys=track_keys,
        source_language=source_language,
        target_language=target_language,
        user_id=None,
        timeout_seconds=3600,
        status_callback=create_status_callback(),
    )

    if not result.success:
        error_msg = (
            f"Multitrack pipeline failed for transcript {result.transcript_id}\n"
        )
        if result.error:
            error_msg += f"Error: {result.error}\n"
        raise RuntimeError(error_msg)

    print_progress(
        f"Multitrack processing complete for transcript {result.transcript_id}"
    )

    # Extract and output results
    database = get_database()
    await database.connect()
    try:
        await extract_result_from_entry(result.transcript_id, output_path)
    finally:
        await database.disconnect()
