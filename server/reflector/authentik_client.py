"""
Authentik API Client
====================

Client for querying Authentik API to fetch all users for synchronization.
"""

import httpx
import structlog

from reflector.settings import settings

logger = structlog.get_logger(__name__)


class AuthentikClient:
    """Client for Authentik API."""

    def __init__(
        self,
        api_url: str | None = None,
        api_token: str | None = None,
    ):
        self.api_url = api_url or settings.AUTHENTIK_API_URL
        self.api_token = api_token or settings.AUTHENTIK_API_TOKEN

        if not self.api_url or not self.api_token:
            logger.warning(
                "Authentik API not configured. "
                "Set AUTHENTIK_API_URL and AUTHENTIK_API_TOKEN environment variables."
            )

    def _get_headers(self) -> dict[str, str]:
        """Get headers for Authentik API requests."""
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Accept": "application/json",
        }

    async def get_all_users(self) -> list[dict]:
        """
        Fetch all users from Authentik with pagination.

        Returns:
            List of all user data dictionaries from all pages
        """
        if not self.api_url or not self.api_token:
            logger.debug("Authentik API not configured, skipping user fetch")
            return []

        all_users = []
        page = 1
        page_size = 100

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                while True:
                    url = f"{self.api_url}/api/v3/core/users/"
                    params = {
                        "page": page,
                        "page_size": page_size,
                        "include_groups": "false",
                    }

                    logger.debug(f"Fetching users from Authentik (page {page})...")
                    response = await client.get(
                        url, headers=self._get_headers(), params=params
                    )
                    response.raise_for_status()
                    data = response.json()

                    results = data.get("results", [])
                    if not results:
                        break

                    all_users.extend(results)
                    logger.debug(f"Fetched {len(results)} users from page {page}")

                    if not data.get("next"):
                        break

                    page += 1

            logger.info(f"Fetched total of {len(all_users)} users from Authentik")
            return all_users

        except httpx.HTTPError as e:
            logger.error(
                "Failed to fetch all users from Authentik",
                error=str(e),
                exc_info=True,
            )
            return []


authentik_client = AuthentikClient()
