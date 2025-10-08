"""Daily.co webhook handler endpoint."""

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from reflector.db.meetings import meetings_controller
from reflector.logger import logger
from reflector.video_platforms.factory import create_platform_client

router = APIRouter()


class DailyWebhookEvent(BaseModel):
    """Daily webhook event structure."""

    version: str
    type: str
    id: str
    payload: Dict[str, Any]
    event_ts: float


@router.post("/webhook")
async def webhook(request: Request):
    """Handle Daily webhook events.

    Daily.co circuit-breaker: After 3+ failed responses (4xx/5xx), webhook
    state→FAILED, stops sending events. Reset: scripts/recreate_daily_webhook.py
    """
    body = await request.body()
    signature = request.headers.get("X-Webhook-Signature", "")
    timestamp = request.headers.get("X-Webhook-Timestamp", "")

    client = create_platform_client("daily")
    if not client.verify_webhook_signature(body, signature, timestamp):
        logger.warning(
            "Invalid webhook signature",
            signature=signature,
            timestamp=timestamp,
            has_body=bool(body),
        )
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse the JSON body
    import json

    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON")

    # Handle Daily's test event during webhook creation
    if body_json.get("test") == "test":
        logger.info("Received Daily webhook test event")
        return {"status": "ok"}

    # Parse as actual event
    try:
        event = DailyWebhookEvent(**body_json)
    except Exception as e:
        logger.error("Failed to parse webhook event", error=str(e), body=body.decode())
        raise HTTPException(status_code=422, detail="Invalid event format")

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
    room_name = event.payload.get("room")
    if not room_name:
        logger.warning("participant.joined: no room in payload", payload=event.payload)
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=current_count + 1
        )
        logger.info(
            "Participant joined",
            meeting_id=meeting.id,
            room_name=room_name,
            num_clients=current_count + 1,
            recording_type=meeting.recording_type,
            recording_trigger=meeting.recording_trigger,
        )
    else:
        logger.warning("participant.joined: meeting not found", room_name=room_name)


async def _handle_participant_left(event: DailyWebhookEvent):
    """Handle participant left event."""
    room_name = event.payload.get("room")
    if not room_name:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=max(0, current_count - 1)
        )


async def _handle_recording_started(event: DailyWebhookEvent):
    """Handle recording started event."""
    # Daily.co inconsistency: participant.* uses "room", recording.* uses "room_name"
    room_name = event.payload.get("room_name") or event.payload.get("room")
    if not room_name:
        logger.warning(
            "recording.started: no room_name in payload", payload=event.payload
        )
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        logger.info(
            "Recording started",
            meeting_id=meeting.id,
            room_name=room_name,
            recording_id=event.payload.get("recording_id"),
            platform="daily",
        )
    else:
        logger.warning("recording.started: meeting not found", room_name=room_name)


async def _handle_recording_ready(event: DailyWebhookEvent):
    """Handle recording ready for download event."""
    room_name = event.payload.get("room")
    recording_id = event.payload.get("recording_id")
    download_link = event.payload.get("download_link")

    if not room_name or not download_link:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        try:
            from reflector.worker.process import process_recording_from_url

            process_recording_from_url.delay(
                recording_url=download_link,
                meeting_id=meeting.id,
                recording_id=recording_id or event.id,
            )
        except ImportError:
            logger.warning(
                "Could not queue recording processing",
                meeting_id=meeting.id,
                room_name=room_name,
                platform="daily",
            )


async def _handle_recording_error(event: DailyWebhookEvent):
    """Handle recording error event."""
    room_name = event.payload.get("room")
    error = event.payload.get("error", "Unknown error")

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
