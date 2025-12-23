"""Webhook task for sending transcript notifications."""

import uuid
from datetime import datetime, timezone

import httpx
import structlog
from celery import shared_task
from celery.utils.log import get_task_logger

from reflector.db.rooms import rooms_controller
from reflector.pipelines.main_live_pipeline import asynctask
from reflector.utils.webhook import (
    WebhookRoomPayload,
    WebhookTestPayload,
    _serialize_payload,
    build_transcript_webhook_payload,
    build_webhook_headers,
    send_webhook_request,
)

logger = structlog.wrap_logger(get_task_logger(__name__))


@shared_task(
    bind=True,
    max_retries=30,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=3600,  # Max 1 hour between retries
)
@asynctask
async def send_transcript_webhook(
    self,
    transcript_id: str,
    room_id: str,
    event_id: str,
):
    """Send webhook notification for completed transcript.

    Uses shared Pydantic models and signature generation from utils/webhook.py
    to ensure consistency with Hatchet pipeline.
    """
    log = logger.bind(
        transcript_id=transcript_id,
        room_id=room_id,
        retry_count=self.request.retries,
    )

    try:
        room = await rooms_controller.get_by_id(room_id)
        if not room:
            log.error("Room not found, skipping webhook")
            return

        if not room.webhook_url:
            log.info("No webhook URL configured for room, skipping")
            return

        payload = await build_transcript_webhook_payload(
            transcript_id=transcript_id,
            room_id=room_id,
        )

        if not payload:
            log.error("Could not build webhook payload, skipping")
            return

        log.info(
            "Sending webhook",
            url=room.webhook_url,
            topics=len(payload.transcript.topics),
            participants=len(payload.transcript.participants),
        )

        response = await send_webhook_request(
            url=room.webhook_url,
            payload=payload,
            event_type="transcript.completed",
            webhook_secret=room.webhook_secret,
            retry_count=self.request.retries,
            timeout=30.0,
        )

        log.info(
            "Webhook sent successfully",
            status_code=response.status_code,
            response_size=len(response.content),
        )

    except httpx.HTTPStatusError as e:
        log.error(
            "Webhook failed with HTTP error",
            status_code=e.response.status_code,
            response_text=e.response.text[:500],  # First 500 chars
        )

        # Don't retry on client errors (4xx)
        if 400 <= e.response.status_code < 500:
            log.error("Client error, not retrying")
            return

        # Retry on server errors (5xx)
        raise self.retry(exc=e)

    except (httpx.ConnectError, httpx.TimeoutException) as e:
        # Retry on network errors
        log.error("Webhook failed with connection error", error=str(e))
        raise self.retry(exc=e)

    except Exception as e:
        # Retry on unexpected errors
        log.exception("Unexpected error in webhook task", error=str(e))
        raise self.retry(exc=e)


async def test_webhook(room_id: str) -> dict:
    """Test webhook configuration by sending a sample payload.

    Returns immediately with success/failure status.
    This is the shared implementation used by both the API endpoint and Celery task.
    """
    try:
        room = await rooms_controller.get_by_id(room_id)
        if not room:
            return {"success": False, "error": "Room not found"}

        if not room.webhook_url:
            return {"success": False, "error": "No webhook URL configured"}

        payload = WebhookTestPayload(
            event="test",
            event_id=uuid.uuid4().hex,
            timestamp=datetime.now(timezone.utc),
            message="This is a test webhook from Reflector",
            room=WebhookRoomPayload(
                id=room.id,
                name=room.name,
            ),
        )

        payload_bytes = _serialize_payload(payload)

        headers = build_webhook_headers(
            event_type="test",
            payload_bytes=payload_bytes,
            webhook_secret=room.webhook_secret,
        )

        # Send test webhook with short timeout
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                room.webhook_url,
                content=payload_bytes,
                headers=headers,
            )

            return {
                "success": response.is_success,
                "status_code": response.status_code,
                "message": f"Webhook test {'successful' if response.is_success else 'failed'}",
                "response_preview": response.text if response.text else None,
            }

    except httpx.TimeoutException:
        return {
            "success": False,
            "error": "Webhook request timed out (10 seconds)",
        }
    except httpx.ConnectError as e:
        return {
            "success": False,
            "error": f"Could not connect to webhook URL: {str(e)}",
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"Unexpected error: {str(e)}",
        }
