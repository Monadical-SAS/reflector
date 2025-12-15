"""Conductor Python client wrapper."""

from conductor.client.configuration.configuration import Configuration
from conductor.client.orkes_clients import OrkesClients
from conductor.client.workflow_client import WorkflowClient
from reflector.settings import settings


class ConductorClientManager:
    """Singleton manager for Conductor client connections."""

    _instance: OrkesClients | None = None

    @classmethod
    def get_client(cls) -> WorkflowClient:
        """Get or create the workflow client."""
        if cls._instance is None:
            config = Configuration(
                server_api_url=settings.CONDUCTOR_SERVER_URL,
                debug=settings.CONDUCTOR_DEBUG,
            )
            cls._instance = OrkesClients(config)
        return cls._instance.get_workflow_client()

    @classmethod
    def start_workflow(cls, name: str, version: int, input_data: dict) -> str:
        """Start a workflow and return the workflow ID."""
        client = cls.get_client()
        return client.start_workflow_by_name(name, input_data, version=version)

    @classmethod
    def get_workflow_status(cls, workflow_id: str) -> dict:
        """Get the current status of a workflow."""
        client = cls.get_client()
        return client.get_workflow(workflow_id, include_tasks=True)

    @classmethod
    def reset(cls) -> None:
        """Reset the client instance (for testing)."""
        cls._instance = None
