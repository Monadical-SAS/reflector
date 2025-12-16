"""Hatchet health and status endpoints."""

from fastapi import APIRouter

from reflector.settings import settings

router = APIRouter(prefix="/hatchet", tags=["hatchet"])


@router.get("/health")
async def hatchet_health():
    """Check Hatchet connectivity and status."""
    if not settings.HATCHET_ENABLED:
        return {"status": "disabled", "connected": False}

    if not settings.HATCHET_CLIENT_TOKEN:
        return {
            "status": "unhealthy",
            "connected": False,
            "error": "HATCHET_CLIENT_TOKEN not configured",
        }

    try:
        from reflector.hatchet.client import HatchetClientManager

        # Get client to verify token is valid
        client = HatchetClientManager.get_client()

        # Try to get the client's gRPC connection status
        # The SDK doesn't have a simple health check, so we just verify we can create the client
        if client is not None:
            return {"status": "healthy", "connected": True}
        else:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": "Failed to create client",
            }
    except ValueError as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}
    except Exception as e:
        return {"status": "unhealthy", "connected": False, "error": str(e)}


@router.get("/workflow/{workflow_run_id}")
async def get_workflow_status(workflow_run_id: str):
    """Get the status of a workflow run."""
    if not settings.HATCHET_ENABLED:
        return {"error": "Hatchet is disabled"}

    try:
        from reflector.hatchet.client import HatchetClientManager

        status = await HatchetClientManager.get_workflow_status(workflow_run_id)
        return status
    except Exception as e:
        return {"error": str(e)}
