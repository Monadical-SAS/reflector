"""
CPU-heavy worker pool for audio processing tasks.
Handles: mixdown_tracks only (serialized with max_runs=1)

Configuration:
- slots=1: Only one mixdown at a time
- Worker affinity: pool=cpu-heavy
"""

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.daily_multitrack_pipeline import (
    daily_multitrack_pipeline,
)
from reflector.logger import logger
from reflector.settings import settings


def main():
    if not settings.HATCHET_ENABLED:
        logger.error("HATCHET_ENABLED is False, not starting CPU workers")
        return

    hatchet = HatchetClientManager.get_client()

    logger.info(
        "Starting Hatchet CPU worker pool (mixdown only)",
        worker_name="cpu-worker-pool",
        slots=1,
        labels={"pool": "cpu-heavy"},
    )

    cpu_worker = hatchet.worker(
        "cpu-worker-pool",
        slots=1,
        labels={
            "pool": "cpu-heavy",
        },
        workflows=[daily_multitrack_pipeline],
    )

    try:
        cpu_worker.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping CPU workers...")


if __name__ == "__main__":
    main()
