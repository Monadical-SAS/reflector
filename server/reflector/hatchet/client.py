"""Hatchet Python client wrapper.

Uses singleton pattern because:
1. Hatchet client maintains persistent gRPC connections for workflow registration
2. Creating multiple clients would cause registration conflicts and resource leaks
3. The SDK is designed for a single client instance per process
4. Tests use `HatchetClientManager.reset()` to isolate state between tests
"""

import logging
import threading

from hatchet_sdk import ClientConfig, Hatchet
from hatchet_sdk.clients.rest.models import V1TaskStatus

from reflector.logger import logger
from reflector.settings import settings


class HatchetClientManager:
    """Singleton manager for Hatchet client connections.

    See module docstring for rationale. For test isolation, use `reset()`.
    """

    _instance: Hatchet | None = None
    _lock = threading.Lock()

    @classmethod
    def get_client(cls) -> Hatchet:
        """Get or create the Hatchet client (thread-safe singleton)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if not settings.HATCHET_CLIENT_TOKEN:
                        raise ValueError("HATCHET_CLIENT_TOKEN must be set")

                    # Pass root logger to Hatchet so workflow logs appear in dashboard
                    root_logger = logging.getLogger()
                    cls._instance = Hatchet(
                        debug=settings.HATCHET_DEBUG,
                        config=ClientConfig(logger=root_logger),
                    )
        return cls._instance

    @classmethod
    async def start_workflow(
        cls,
        workflow_name: str,
        input_data: dict,
        additional_metadata: dict | None = None,
    ) -> str:
        """Start a workflow and return the workflow run ID.

        Args:
            workflow_name: Name of the workflow to trigger.
            input_data: Input data for the workflow run.
            additional_metadata: Optional metadata for filtering in dashboard
                (e.g., transcript_id, recording_id).
        """
        client = cls.get_client()
        result = await client.runs.aio_create(
            workflow_name,
            input_data,
            additional_metadata=additional_metadata,
        )
        return result.run.metadata.id

    @classmethod
    async def get_workflow_run_status(cls, workflow_run_id: str) -> V1TaskStatus:
        client = cls.get_client()
        return await client.runs.aio_get_status(workflow_run_id)

    @classmethod
    async def cancel_workflow(cls, workflow_run_id: str) -> None:
        client = cls.get_client()
        await client.runs.aio_cancel(workflow_run_id)
        logger.info("[Hatchet] Cancelled workflow", workflow_run_id=workflow_run_id)

    @classmethod
    async def replay_workflow(cls, workflow_run_id: str) -> None:
        client = cls.get_client()
        await client.runs.aio_replay(workflow_run_id)
        logger.info("[Hatchet] Replaying workflow", workflow_run_id=workflow_run_id)

    @classmethod
    async def can_replay(cls, workflow_run_id: str) -> bool:
        """Check if workflow can be replayed (is FAILED)."""
        try:
            status = await cls.get_workflow_run_status(workflow_run_id)
            return status == V1TaskStatus.FAILED
        except Exception as e:
            logger.warning(
                "[Hatchet] Failed to check replay status",
                workflow_run_id=workflow_run_id,
                error=str(e),
            )
            return False

    @classmethod
    async def get_workflow_status(cls, workflow_run_id: str) -> dict:
        """Get the full workflow run details as dict."""
        client = cls.get_client()
        run = await client.runs.aio_get(workflow_run_id)
        return run.to_dict()

    @classmethod
    def reset(cls) -> None:
        """Reset the client instance (for testing)."""
        with cls._lock:
            cls._instance = None
