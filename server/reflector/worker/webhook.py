"""Webhook task for sending transcript notifications."""

import hashlib
import hmac
import json
from datetime import datetime, timezone

import httpx
import structlog
from celery import shared_task
from celery.utils.log import get_task_logger

from reflector.db.rooms import rooms_controller
from reflector.db.transcripts import transcripts_controller
from reflector.pipelines.main_live_pipeline import asynctask
from reflector.settings import settings
from reflector.utils.webvtt import topics_to_webvtt

logger = structlog.wrap_logger(get_task_logger(__name__))


def generate_webhook_signature(payload: bytes, secret: str, timestamp: str) -> str:
    """Generate HMAC signature for webhook payload."""
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    hmac_obj = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    )
    return hmac_obj.hexdigest()


@shared_task(
    bind=True,
    max_retries=30,
    default_retry_delay=60,
    retry_backoff=True,
    retry_backoff_max=3600,  # Max 1 hour between retries
)
@asynctask
async def send_transcript_webhook(self, transcript_id: str, room_id: str):
    log = logger.bind(
        transcript_id=transcript_id,
        room_id=room_id,
        retry_count=self.request.retries,
    )

    try:
        # Fetch transcript and room
        transcript = await transcripts_controller.get_by_id(transcript_id)
        if not transcript:
            log.error("Transcript not found, skipping webhook")
            return

        room = await rooms_controller.get_by_id(room_id)
        if not room:
            log.error("Room not found, skipping webhook")
            return

        if not room.webhook_url:
            log.info("No webhook URL configured for room, skipping")
            return

        # Generate WebVTT content from topics
        topics_data = []

        if transcript.topics:
            # Build topics data with diarized content per topic
            for topic in transcript.topics:
                topic_webvtt = topics_to_webvtt([topic]) if topic.words else ""
                topics_data.append(
                    {
                        "title": topic.title,
                        "summary": topic.summary,
                        "timestamp": topic.timestamp,
                        "duration": topic.duration,
                        "webvtt": topic_webvtt,
                    }
                )

        # Build webhook payload
        frontend_url = f"{settings.UI_BASE_URL}/transcripts/{transcript.id}"
        participants = [
            {"id": p.id, "name": p.name, "speaker": p.speaker}
            for p in (transcript.participants or [])
        ]
        payload_data = {
            "event": "transcript.completed",
            "event_id": f"transcript.completed-{transcript.id}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "transcript": {
                "id": transcript.id,
                "room_id": transcript.room_id,
                "created_at": transcript.created_at.isoformat(),
                "duration": transcript.duration,
                "title": transcript.title,
                "short_summary": transcript.short_summary,
                "long_summary": transcript.long_summary,
                "webvtt": transcript.webvtt,
                "topics": topics_data,
                "participants": participants,
                "source_language": transcript.source_language,
                "target_language": transcript.target_language,
                "status": transcript.status,
                "frontend_url": frontend_url,
            },
            "room": {
                "id": room.id,
                "name": room.name,
            },
        }

        # Convert to JSON
        payload_json = json.dumps(payload_data, separators=(",", ":"))
        payload_bytes = payload_json.encode("utf-8")

        # Generate signature if secret is configured
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Reflector-Webhook/1.0",
            "X-Webhook-Event": "transcript.completed",
            "X-Webhook-Retry": str(self.request.retries),
        }

        if room.webhook_secret:
            timestamp = str(int(datetime.now(timezone.utc).timestamp()))
            signature = generate_webhook_signature(
                payload_bytes, room.webhook_secret, timestamp
            )
            headers["X-Webhook-Signature"] = f"t={timestamp},v1={signature}"

        # Send webhook with timeout
        async with httpx.AsyncClient(timeout=30.0) as client:
            log.info(
                "Sending webhook",
                url=room.webhook_url,
                payload_size=len(payload_bytes),
            )

            response = await client.post(
                room.webhook_url,
                content=payload_bytes,
                headers=headers,
            )

            response.raise_for_status()

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
    """
    Test webhook configuration by sending a sample payload.
    Returns immediately with success/failure status.
    This is the shared implementation used by both the API endpoint and Celery task.
    """
    try:
        room = await rooms_controller.get_by_id(room_id)
        if not room:
            return {"success": False, "error": "Room not found"}

        if not room.webhook_url:
            return {"success": False, "error": "No webhook URL configured"}

        now = (datetime.now(timezone.utc).isoformat(),)
        payload_data = {
            "event": "test",
            "event_id": f"test-{now}",
            "timestamp": now,
            "message": "This is a test webhook from Reflector",
            "room": {
                "id": room.id,
                "name": room.name,
            },
        }

        payload_json = json.dumps(payload_data, separators=(",", ":"))
        payload_bytes = payload_json.encode("utf-8")

        # Generate headers with signature
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Reflector-Webhook/1.0",
            "X-Webhook-Event": "test",
        }

        if room.webhook_secret:
            timestamp = str(int(datetime.now(timezone.utc).timestamp()))
            signature = generate_webhook_signature(
                payload_bytes, room.webhook_secret, timestamp
            )
            headers["X-Webhook-Signature"] = f"t={timestamp},v1={signature}"

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
