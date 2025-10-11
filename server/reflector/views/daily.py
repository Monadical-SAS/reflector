"""Daily.co webhook handler endpoint."""

import json
from typing import Any, Dict, Literal

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from reflector.db.meetings import meetings_controller
from reflector.logger import logger
from reflector.video_platforms.factory import create_platform_client

router = APIRouter()


class DailyTrack(BaseModel):
    """Daily.co recording track (audio or video file)."""

    type: Literal["audio", "video"]
    s3Key: str
    size: int


class DailyWebhookEvent(BaseModel):
    """Daily webhook event structure."""

    version: str
    type: str
    id: str
    payload: Dict[str, Any]
    event_ts: float


def _extract_room_name(event: DailyWebhookEvent) -> str | None:
    """Extract room name from Daily event payload.

    Daily.co API inconsistency:
    - participant.* events use "room" field
    - recording.* events use "room_name" field
    """
    return event.payload.get("room_name") or event.payload.get("room")


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

    # TEMPORARY: Bypass signature check for testing
    # TODO: Remove this after testing is complete
    BYPASS_FOR_TESTING = True
    if not BYPASS_FOR_TESTING:
        if not client.verify_webhook_signature(body, signature, timestamp):
            logger.warning(
                "Invalid webhook signature",
                signature=signature,
                timestamp=timestamp,
                has_body=bool(body),
            )
            raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Parse the JSON body
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
    room_name = _extract_room_name(event)
    if not room_name:
        logger.warning("participant.joined: no room in payload", payload=event.payload)
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        await meetings_controller.increment_num_clients(meeting.id)
        logger.info(
            "Participant joined",
            meeting_id=meeting.id,
            room_name=room_name,
            recording_type=meeting.recording_type,
            recording_trigger=meeting.recording_trigger,
        )
    else:
        logger.warning("participant.joined: meeting not found", room_name=room_name)


async def _handle_participant_left(event: DailyWebhookEvent):
    """Handle participant left event."""
    room_name = _extract_room_name(event)
    if not room_name:
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        await meetings_controller.decrement_num_clients(meeting.id)


async def _handle_recording_started(event: DailyWebhookEvent):
    """Handle recording started event."""
    room_name = _extract_room_name(event)
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
    """Handle recording ready for download event.

    Daily.co webhook payload for raw-tracks recordings:
    {
      "recording_id": "...",
      "room_name": "test2-20251009192341",
      "tracks": [
        {"type": "audio", "s3Key": "monadical/test2-.../uuid-cam-audio-123.webm", "size": 400000},
        {"type": "video", "s3Key": "monadical/test2-.../uuid-cam-video-456.webm", "size": 30000000}
      ]
    }
    """
    room_name = _extract_room_name(event)
    recording_id = event.payload.get("recording_id")
    tracks_raw = event.payload.get("tracks", [])

    if not room_name or not tracks_raw:
        logger.warning(
            "recording.ready-to-download: missing room_name or tracks",
            room_name=room_name,
            has_tracks=bool(tracks_raw),
            payload=event.payload,
        )
        return

    # Validate tracks structure
    try:
        tracks = [DailyTrack(**t) for t in tracks_raw]
    except Exception as e:
        logger.error(
            "recording.ready-to-download: invalid tracks structure",
            error=str(e),
            tracks=tracks_raw,
        )
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if not meeting:
        logger.warning(
            "recording.ready-to-download: meeting not found", room_name=room_name
        )
        return

    logger.info(
        "Recording ready for download",
        meeting_id=meeting.id,
        room_name=room_name,
        recording_id=recording_id,
        num_tracks=len(tracks),
        platform="daily",
    )

    # Import at runtime to avoid circular dependency (process.py imports from daily.py)
    from reflector.worker.process import process_daily_recording  # noqa: PLC0415

    # Convert Pydantic models to dicts for Celery serialization
    process_daily_recording.delay(
        meeting_id=meeting.id,
        recording_id=recording_id or event.id,
        tracks=[t.model_dump() for t in tracks],
    )


async def _handle_recording_error(event: DailyWebhookEvent):
    """Handle recording error event."""
    room_name = _extract_room_name(event)
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
