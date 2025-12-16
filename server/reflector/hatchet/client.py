"""Hatchet Python client wrapper."""

from hatchet_sdk import Hatchet

from reflector.logger import logger
from reflector.settings import settings


class HatchetClientManager:
    """Singleton manager for Hatchet client connections."""

    _instance: Hatchet | None = None

    @classmethod
    def get_client(cls) -> Hatchet:
        """Get or create the Hatchet client."""
        if cls._instance is None:
            if not settings.HATCHET_CLIENT_TOKEN:
                raise ValueError("HATCHET_CLIENT_TOKEN must be set")

            cls._instance = Hatchet(
                debug=settings.HATCHET_DEBUG,
            )
        return cls._instance

    @classmethod
    async def start_workflow(
        cls, workflow_name: str, input_data: dict, key: str | None = None
    ) -> str:
        """Start a workflow and return the workflow run ID."""
        client = cls.get_client()
        result = await client.runs.aio_create(
            workflow_name,
            input_data,
        )
        # SDK v1.21+ returns V1WorkflowRunDetails with run.metadata.id
        return result.run.metadata.id

    @classmethod
    async def get_workflow_run_status(cls, workflow_run_id: str) -> str:
        """Get workflow run status."""
        client = cls.get_client()
        status = await client.runs.aio_get_status(workflow_run_id)
        return str(status)

    @classmethod
    async def cancel_workflow(cls, workflow_run_id: str) -> None:
        """Cancel a workflow."""
        client = cls.get_client()
        await client.runs.aio_cancel(workflow_run_id)
        logger.info("[Hatchet] Cancelled workflow", workflow_run_id=workflow_run_id)

    @classmethod
    async def replay_workflow(cls, workflow_run_id: str) -> None:
        """Replay a failed workflow."""
        client = cls.get_client()
        await client.runs.aio_replay(workflow_run_id)
        logger.info("[Hatchet] Replaying workflow", workflow_run_id=workflow_run_id)

    @classmethod
    async def can_replay(cls, workflow_run_id: str) -> bool:
        """Check if workflow can be replayed (is FAILED)."""
        try:
            status = await cls.get_workflow_run_status(workflow_run_id)
            return "FAILED" in status
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
        cls._instance = None
