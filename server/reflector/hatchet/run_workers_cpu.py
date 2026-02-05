"""
CPU-heavy worker pool for audio processing tasks.
Handles ONLY: mixdown_tracks

Configuration:
- slots=1: Only mixdown (already serialized globally with max_runs=1)
- Worker affinity: pool=cpu-heavy
"""

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.daily_multitrack_pipeline import (
    daily_multitrack_pipeline,
)
from reflector.logger import logger


def main():
    hatchet = HatchetClientManager.get_client()

    logger.info(
        "Starting Hatchet CPU worker pool (mixdown only)",
        worker_name="cpu-worker-pool",
        slots=1,
        labels={"pool": "cpu-heavy"},
    )

    cpu_worker = hatchet.worker(
        "cpu-worker-pool",
        slots=1,  # Only 1 mixdown at a time (already serialized globally)
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
