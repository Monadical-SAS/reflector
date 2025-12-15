"""Conductor health and status endpoints."""

import httpx
from fastapi import APIRouter

from reflector.settings import settings

router = APIRouter(prefix="/conductor", tags=["conductor"])


@router.get("/health")
async def conductor_health():
    """Check Conductor server connectivity and status."""
    if not settings.CONDUCTOR_ENABLED:
        return {"status": "disabled", "connected": False}

    # Extract base URL (remove /api suffix for health check)
    base_url = settings.CONDUCTOR_SERVER_URL.rstrip("/api").rstrip("/")
    health_url = f"{base_url}/health"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(health_url)
            if resp.status_code == 200:
                return {"status": "healthy", "connected": True}
            else:
                return {
                    "status": "unhealthy",
                    "connected": True,
                    "error": f"Health check returned {resp.status_code}",
                }
    except httpx.TimeoutException:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": "Connection timeout",
        }
    except httpx.ConnectError as e:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": f"Connection failed: {e}",
        }
    except Exception as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}
