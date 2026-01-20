"""
LLM/I/O worker pool for all non-CPU tasks.
Handles: all tasks except mixdown_tracks (transcription, LLM inference, orchestration)
"""

from reflector.hatchet.client import HatchetClientManager
from reflector.hatchet.workflows.daily_multitrack_pipeline import (
    daily_multitrack_pipeline,
)
from reflector.hatchet.workflows.subject_processing import subject_workflow
from reflector.hatchet.workflows.topic_chunk_processing import topic_chunk_workflow
from reflector.hatchet.workflows.track_processing import track_workflow
from reflector.logger import logger
from reflector.settings import settings


def main():
    if not settings.HATCHET_ENABLED:
        logger.error("HATCHET_ENABLED is False, not starting LLM workers")
        return

    hatchet = HatchetClientManager.get_client()

    logger.info(
        "Starting Hatchet LLM worker pool (all tasks except mixdown)",
        worker_name="llm-worker-pool",
        slots=10,
        labels={"pool": "llm-io"},
    )

    llm_worker = hatchet.worker(
        "llm-worker-pool",
        slots=10,  # High concurrency OK for I/O-bound tasks
        labels={
            "pool": "llm-io",
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
