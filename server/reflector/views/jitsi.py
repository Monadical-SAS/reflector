import hmac
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from reflector.db.meetings import meetings_controller
from reflector.settings import settings

try:
    from reflector.video_platforms import create_platform_client
except ImportError:
    # PyJWT not yet installed, will be added in final task
    def create_platform_client(platform: str):
        return None


router = APIRouter()


class JitsiWebhookEvent(BaseModel):
    event: str
    room: str
    timestamp: datetime
    data: Dict[str, Any] = {}


class JibriRecordingEvent(BaseModel):
    room_name: str
    recording_file: str
    recording_status: str
    timestamp: datetime


def verify_jitsi_webhook_signature(body: bytes, signature: str) -> bool:
    """Verify Jitsi webhook signature using HMAC-SHA256."""
    if not signature or not settings.JITSI_WEBHOOK_SECRET:
        return False

    try:
        client = create_platform_client("jitsi")
        if client is None:
            # Fallback verification when platform client not available
            expected = hmac.new(
                settings.JITSI_WEBHOOK_SECRET.encode(), body, sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        return client.verify_webhook_signature(body, signature)
    except Exception:
        return False


@router.post("/jitsi/events")
async def jitsi_events_webhook(event: JitsiWebhookEvent, request: Request):
    """
    Handle Prosody event-sync webhooks from Jitsi Meet.

    Expected event types:
    - muc-occupant-joined: participant joined the room
    - muc-occupant-left: participant left the room
    - jibri-recording-on: recording started
    - jibri-recording-off: recording stopped
    """
    # Verify webhook signature
    body = await request.body()
    signature = request.headers.get("x-jitsi-signature", "")

    if not verify_jitsi_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Find meeting by room name
    meeting = await meetings_controller.get_by_room_name(event.room)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # Handle participant events
    if event.event == "muc-occupant-joined":
        # Get current participant count and increment
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=current_count + 1
        )
    elif event.event == "muc-occupant-left":
        # Get current participant count and decrement (minimum 0)
        current_count = getattr(meeting, "num_clients", 0)
        await meetings_controller.update_meeting(
            meeting.id, num_clients=max(0, current_count - 1)
        )
    elif event.event == "jibri-recording-on":
        # Recording started - could update meeting status if needed
        # For now, we just acknowledge the event
        pass
    elif event.event == "jibri-recording-off":
        # Recording stopped - could trigger processing pipeline
        # This would be where we initiate transcript processing
        pass

    return {"status": "ok", "event": event.event, "room": event.room}


@router.post("/jibri/recording-complete")
async def jibri_recording_complete(event: JibriRecordingEvent, request: Request):
    """
    Handle Jibri recording completion webhook.

    This endpoint is called by the Jibri finalize script when a recording
    is completed and uploaded to storage.
    """
    # Verify webhook signature
    body = await request.body()
    signature = request.headers.get("x-jitsi-signature", "")

    if not verify_jitsi_webhook_signature(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    # Find meeting by room name
    meeting = await meetings_controller.get_by_room_name(event.room_name)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    # TODO: Trigger recording processing pipeline
    # This is where we would:
    # 1. Download the recording file from Jibri storage
    # 2. Create a transcript record in the database
    # 3. Queue the audio processing tasks (chunking, transcription, etc.)
    # 4. Update meeting status to indicate recording is being processed

    return {
        "status": "ok",
        "room_name": event.room_name,
        "recording_file": event.recording_file,
        "message": "Recording processing queued",
    }


@router.get("/jitsi/health")
async def jitsi_health_check():
    """Simple health check endpoint for Jitsi webhook configuration."""
    return {
        "status": "ok",
        "service": "jitsi-webhooks",
        "timestamp": datetime.utcnow().isoformat(),
        "webhook_secret_configured": bool(settings.JITSI_WEBHOOK_SECRET),
    }
