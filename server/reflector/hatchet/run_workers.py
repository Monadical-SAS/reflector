"""
Run Hatchet workers for the diarization pipeline.

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

    # Import here (not top-level) - workflow imports trigger HatchetClientManager.get_client()
    # which requires HATCHET_CLIENT_TOKEN; must validate settings first
    from reflector.hatchet.client import HatchetClientManager  # noqa: PLC0415
    from reflector.hatchet.workflows import (  # noqa: PLC0415
        diarization_pipeline,
        track_workflow,
    )

    hatchet = HatchetClientManager.get_client()

    # Create worker with both workflows
    worker = hatchet.worker(
        "reflector-diarization-worker",
        workflows=[diarization_pipeline, track_workflow],
    )

    # Handle graceful shutdown
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
