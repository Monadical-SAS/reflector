"""
LLM/I/O worker pool for all non-CPU tasks.
Handles: all tasks except mixdown_tracks (transcription, LLM inference, orchestration)
"""

import asyncio

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.daily_multitrack_pipeline import (
    daily_multitrack_pipeline,
)
from reflector.hatchet.workflows.subject_processing import subject_workflow
from reflector.hatchet.workflows.topic_chunk_processing import topic_chunk_workflow
from reflector.hatchet.workflows.track_processing import track_workflow
from reflector.logger import logger

SLOTS = 10
WORKER_NAME = "llm-worker-pool"
POOL = "llm-io"


def main():
    hatchet = HatchetClientManager.get_client()

    try:
        asyncio.run(HatchetClientManager.ensure_rate_limit())
    except Exception as e:
        logger.warning(
            "[Hatchet] Rate limit initialization failed, but continuing. "
            "If workflows fail to register, rate limits may need to be created manually.",
            error=str(e),
        )

    logger.info(
        "Starting Hatchet LLM worker pool (all tasks except mixdown)",
        worker_name=WORKER_NAME,
        slots=SLOTS,
        labels={"pool": POOL},
    )

    llm_worker = hatchet.worker(
        WORKER_NAME,
        slots=SLOTS,  # not all slots are probably used
        labels={
            "pool": POOL,
        },
        workflows=[
            daily_multitrack_pipeline,
            topic_chunk_workflow,
            subject_workflow,
            track_workflow,
        ],
    )

    try:
        llm_worker.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping LLM workers...")


if __name__ == "__main__":
    main()
