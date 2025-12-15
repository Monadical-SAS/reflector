"""Register workflow definition with Conductor server."""

import json
from pathlib import Path

import httpx

from reflector.logger import logger
from reflector.settings import settings


def register_workflow() -> None:
    """Register the diarization pipeline workflow with Conductor server.

    Raises:
        httpx.HTTPStatusError: If registration fails.
    """
    workflow_path = Path(__file__).parent / "diarization_pipeline.json"

    with open(workflow_path) as f:
        workflow = json.load(f)

    base_url = settings.CONDUCTOR_SERVER_URL.rstrip("/")
    url = f"{base_url}/metadata/workflow"

    logger.info(
        "Registering workflow",
        name=workflow["name"],
        version=workflow["version"],
        url=url,
    )

    with httpx.Client(timeout=30.0) as client:
        resp = client.put(
            url,
            json=[workflow],
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()

    logger.info("Workflow registered successfully", name=workflow["name"])


async def register_workflow_async() -> None:
    """Async version of register_workflow."""
    workflow_path = Path(__file__).parent / "diarization_pipeline.json"

    with open(workflow_path) as f:
        workflow = json.load(f)

    base_url = settings.CONDUCTOR_SERVER_URL.rstrip("/")
    url = f"{base_url}/metadata/workflow"

    logger.info(
        "Registering workflow",
        name=workflow["name"],
        version=workflow["version"],
        url=url,
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.put(
            url,
            json=[workflow],
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()

    logger.info("Workflow registered successfully", name=workflow["name"])


if __name__ == "__main__":
    register_workflow()
    print("Workflow registration complete!")
