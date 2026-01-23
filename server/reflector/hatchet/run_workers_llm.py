"""
LLM/I/O worker pool for all non-CPU tasks.
Handles: all tasks except mixdown_tracks (padding, transcription, LLM inference, orchestration)
"""

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.daily_multitrack_pipeline import (
    daily_multitrack_pipeline,
)
from reflector.hatchet.workflows.padding_workflow import padding_workflow
from reflector.hatchet.workflows.subject_processing import subject_workflow
from reflector.hatchet.workflows.topic_chunk_processing import topic_chunk_workflow
from reflector.hatchet.workflows.transcription_workflow import transcription_workflow
from reflector.logger import logger
from reflector.settings import settings

SLOTS = 10
WORKER_NAME = "llm-worker-pool"
POOL = "llm-io"


def main():
    if not settings.HATCHET_ENABLED:
        logger.error("HATCHET_ENABLED is False, not starting LLM workers")
        return

    hatchet = HatchetClientManager.get_client()

    logger.info(
        "Starting Hatchet LLM worker pool (all tasks except mixdown)",
        worker_name=WORKER_NAME,
        slots=SLOTS,
        labels={"pool": POOL},
    )

    llm_worker = hatchet.worker(
        WORKER_NAME,
        slots=SLOTS,
        labels={
            "pool": POOL,
        },
        workflows=[
            daily_multitrack_pipeline,
            topic_chunk_workflow,
            subject_workflow,
            padding_workflow,
            transcription_workflow,
        ],
    )

    try:
        llm_worker.start()
    except KeyboardInterrupt:
        logger.info("Received shutdown signal, stopping LLM workers...")


if __name__ == "__main__":
    main()
