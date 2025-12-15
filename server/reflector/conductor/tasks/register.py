"""Register task definitions with Conductor server."""

import httpx

from reflector.conductor.tasks.definitions import TASK_DEFINITIONS
from reflector.logger import logger
from reflector.settings import settings


def register_task_definitions() -> None:
    """Register all task definitions with Conductor server.

    Raises:
        httpx.HTTPStatusError: If registration fails.
    """
    base_url = settings.CONDUCTOR_SERVER_URL.rstrip("/")
    url = f"{base_url}/metadata/taskdefs"

    logger.info(
        "Registering task definitions",
        count=len(TASK_DEFINITIONS),
        url=url,
    )

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            url,
            json=TASK_DEFINITIONS,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()

    logger.info("Task definitions registered successfully")


async def register_task_definitions_async() -> None:
    """Async version of register_task_definitions."""
    base_url = settings.CONDUCTOR_SERVER_URL.rstrip("/")
    url = f"{base_url}/metadata/taskdefs"

    logger.info(
        "Registering task definitions",
        count=len(TASK_DEFINITIONS),
        url=url,
    )

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            url,
            json=TASK_DEFINITIONS,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()

    logger.info("Task definitions registered successfully")


if __name__ == "__main__":
    register_task_definitions()
    print(f"Registered {len(TASK_DEFINITIONS)} task definitions")
