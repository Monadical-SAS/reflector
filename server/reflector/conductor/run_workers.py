"""
Run Conductor workers for the diarization pipeline.

Usage:
    uv run -m reflector.conductor.run_workers

    # Or via docker:
    docker compose exec server uv run -m reflector.conductor.run_workers
"""

import signal
import sys
import time

from conductor.client.automator.task_handler import TaskHandler
from conductor.client.configuration.configuration import Configuration
from reflector.conductor import workers  # noqa: F401 - registers workers via decorators
from reflector.logger import logger
from reflector.settings import settings


def main() -> None:
    """Start Conductor worker polling."""
    if not settings.CONDUCTOR_ENABLED:
        logger.error("CONDUCTOR_ENABLED is False, not starting workers")
        sys.exit(1)

    logger.info(
        "Starting Conductor workers",
        server_url=settings.CONDUCTOR_SERVER_URL,
    )

    config = Configuration(
        server_api_url=settings.CONDUCTOR_SERVER_URL,
        debug=settings.CONDUCTOR_DEBUG,
    )

    task_handler = TaskHandler(configuration=config)

    # Handle graceful shutdown
    def shutdown_handler(signum: int, frame) -> None:
        logger.info("Received shutdown signal, stopping workers...")
        task_handler.stop_processes()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    logger.info("Starting task polling...")
    task_handler.start_processes()

    # Keep alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()
