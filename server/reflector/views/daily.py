"""Daily.co webhook handler endpoint."""

import hmac
from hashlib import sha256
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from reflector.db.meetings import meetings_controller
from reflector.logger import logger
from reflector.settings import settings

router = APIRouter()


class DailyWebhookEvent(BaseModel):
    """Daily webhook event structure."""

    type: str
    id: str
    ts: int  # Unix timestamp in milliseconds
    data: Dict[str, Any]


def verify_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Daily webhook signature using HMAC-SHA256."""
    if not signature or not settings.DAILY_WEBHOOK_SECRET:
        return False

    try:
        expected = hmac.new(
            settings.DAILY_WEBHOOK_SECRET.encode(), body, sha256
        ).hexdigest()
        return hmac.compare_digest(expected, signature)
    except Exception:
        return False


@router.post("/webhook")
async def webhook(event: DailyWebhookEvent, request: Request):
    """Handle Daily webhook events."""
    # Verify webhook signature for security
    body = await request.body()
    signature = request.headers.get("X-Daily-Signature", "")

    if not verify_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Handle participant events
    if event.type == "participant.joined":
        await _handle_participant_joined(event)
    elif event.type == "participant.left":
        await _handle_participant_left(event)
    elif event.type == "recording.started":
        await _handle_recording_started(event)
    elif event.type == "recording.ready-to-download":
        await _handle_recording_ready(event)
    elif event.type == "recording.error":
        await _handle_recording_error(event)

    return {"status": "ok"}


async def _handle_participant_joined(event: DailyWebhookEvent):
    """Handle participant joined event."""
    room_name = event.data.get("room", {}).get("name")
    if not room_name:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        # Update participant count (same as Whereby)
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=current_count + 1
        )


async def _handle_participant_left(event: DailyWebhookEvent):
    """Handle participant left event."""
    room_name = event.data.get("room", {}).get("name")
    if not room_name:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        # Update participant count (same as Whereby)
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=max(0, current_count - 1)
        )


async def _handle_recording_started(event: DailyWebhookEvent):
    """Handle recording started event."""
    room_name = event.data.get("room", {}).get("name")
    if not room_name:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        # Log recording start for debugging
        logger.info(
            "Recording started",
            meeting_id=meeting.id,
            room_name=room_name,
            platform="daily",
        )


async def _handle_recording_ready(event: DailyWebhookEvent):
    """Handle recording ready for download event."""
    room_name = event.data.get("room", {}).get("name")
    recording_data = event.data.get("recording", {})
    download_link = recording_data.get("download_url")
    recording_id = recording_data.get("id")

    if not room_name or not download_link:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        # Queue recording processing task (same as Whereby)
        try:
            # Import here to avoid circular imports
            from reflector.worker.process import process_recording_from_url

            # For Daily.co, we need to queue recording processing with URL
            # This will download from the URL and process similar to S3
            process_recording_from_url.delay(
                recording_url=download_link,
                meeting_id=meeting.id,
                recording_id=recording_id or event.id,
            )
        except ImportError:
            # Handle case where worker tasks aren't available
            logger.warning(
                "Could not queue recording processing",
                meeting_id=meeting.id,
                room_name=room_name,
                platform="daily",
            )


async def _handle_recording_error(event: DailyWebhookEvent):
    """Handle recording error event."""
    room_name = event.data.get("room", {}).get("name")
    error = event.data.get("error", "Unknown error")

    if room_name:
        meeting = await meetings_controller.get_by_room_name(room_name)
        if meeting:
            logger.error(
                "Recording error",
                meeting_id=meeting.id,
                room_name=room_name,
                error=error,
                platform="daily",
            )
