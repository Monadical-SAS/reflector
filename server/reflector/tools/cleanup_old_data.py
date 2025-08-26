#!/usr/bin/env python
"""
Manual cleanup tool for old public data.
Uses the same implementation as the Celery worker task.
"""

import argparse
import asyncio
import sys
from unittest.mock import patch

import structlog

from reflector.settings import settings
from reflector.worker.cleanup import _cleanup_old_public_data

logger = structlog.get_logger(__name__)


async def cleanup_old_data(days: int = 7):
    """
    Run cleanup with a custom retention period.
    
    Args:
        days: Number of days to keep data (default: 7)
    """
    logger.info(
        "Starting manual cleanup",
        retention_days=days,
        public_mode=settings.PUBLIC_MODE,
    )

    if not settings.PUBLIC_MODE:
        logger.warning(
            "WARNING: PUBLIC_MODE is False. "
            "This tool is intended for public instances. "
            "Proceeding anyway - be careful!"
        )

    # Temporarily override the retention days setting
    with patch.object(settings, "PUBLIC_DATA_RETENTION_DAYS", days):
        # Temporarily enable PUBLIC_MODE if not set
        with patch.object(settings, "PUBLIC_MODE", True):
            result = await _cleanup_old_public_data()

    if result:
        logger.info(
            "Cleanup completed",
            transcripts_deleted=result.get("transcripts_deleted", 0),
            meetings_deleted=result.get("meetings_deleted", 0),
            recordings_deleted=result.get("recordings_deleted", 0),
            errors_count=len(result.get("errors", [])),
        )
        if result.get("errors"):
            logger.warning("Errors encountered during cleanup:", errors=result["errors"][:10])
    else:
        logger.info("Cleanup skipped or completed without results")


def main():
    parser = argparse.ArgumentParser(
        description="Clean up old transcripts and meetings"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=7,
        help="Number of days to keep data (default: 7)",
    )

    args = parser.parse_args()

    if args.days < 1:
        logger.error("Days must be at least 1")
        sys.exit(1)

    asyncio.run(cleanup_old_data(days=args.days))


if __name__ == "__main__":
    main()