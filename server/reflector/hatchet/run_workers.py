"""
Run Hatchet workers for the diarization pipeline.
Runs as a separate process, just like Celery workers.

Usage:
    uv run -m reflector.hatchet.run_workers

    # Or via docker:
    docker compose exec server uv run -m reflector.hatchet.run_workers
"""

import signal
import sys

from reflector.logger import logger
from reflector.settings import settings


def main() -> None:
    """Start Hatchet worker polling."""
    if not settings.HATCHET_ENABLED:
        logger.error("HATCHET_ENABLED is False, not starting workers")
        sys.exit(1)

    if not settings.HATCHET_CLIENT_TOKEN:
        logger.error("HATCHET_CLIENT_TOKEN is not set")
        sys.exit(1)

    logger.info(
        "Starting Hatchet workers",
        debug=settings.HATCHET_DEBUG,
    )

    # Import here (not top-level) - workflow modules call HatchetClientManager.get_client()
    # at module level because Hatchet SDK decorators (@workflow.task) bind at import time.
    # Can't use lazy init: decorators need the client object when function is defined.
    from reflector.hatchet.client import HatchetClientManager  # noqa: PLC0415
    from reflector.hatchet.workflows import (  # noqa: PLC0415
        diarization_pipeline,
        subject_workflow,
        topic_chunk_workflow,
        track_workflow,
    )

    hatchet = HatchetClientManager.get_client()

    worker = hatchet.worker(
        "reflector-diarization-worker",
        workflows=[
            diarization_pipeline,
            subject_workflow,
            topic_chunk_workflow,
            track_workflow,
        ],
    )

    def shutdown_handler(signum: int, frame) -> None:
        logger.info("Received shutdown signal, stopping workers...")
        # Worker cleanup happens automatically on exit
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Starting Hatchet worker polling...")
    worker.start()


if __name__ == "__main__":
    main()
