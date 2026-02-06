import json
from datetime import datetime, timezone
from typing import assert_never

from fastapi import APIRouter, HTTPException, Request
from pydantic import TypeAdapter

from reflector.dailyco_api import (
    DailyWebhookEventUnion,
    ParticipantJoinedEvent,
    ParticipantLeftEvent,
    RecordingErrorEvent,
    RecordingReadyEvent,
    RecordingStartedEvent,
)
from reflector.db.daily_participant_sessions import (
    daily_participant_sessions_controller,
)
from reflector.db.meetings import meetings_controller
from reflector.logger import logger as _logger
from reflector.settings import settings
from reflector.video_platforms.factory import create_platform_client
from reflector.worker.process import (
    poll_daily_room_presence_task,
    process_multitrack_recording,
    store_cloud_recording,
)

router = APIRouter()

logger = _logger.bind(platform="daily")


@router.post("/webhook")
async def webhook(request: Request):
    """Handle Daily webhook events.

    Example webhook payload:
    {
      "version": "1.0.0",
      "type": "recording.ready-to-download",
      "id": "rec-rtd-c3df927c-f738-4471-a2b7-066fa7e95a6b-1692124192",
      "payload": {
        "recording_id": "08fa0b24-9220-44c5-846c-3f116cf8e738",
        "room_name": "Xcm97xRZ08b2dePKb78g",
        "start_ts": 1692124183,
        "status": "finished",
        "max_participants": 1,
        "duration": 9,
        "share_token": "ntDCL5k98Ulq", #gitleaks:allow
        "s3_key": "api-test-1j8fizhzd30c/Xcm97xRZ08b2dePKb78g/1692124183028"
      },
      "event_ts": 1692124192
    }

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

    try:
        body_json = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="Invalid JSON")

    if body_json.get("test") == "test":
        logger.info("Received Daily webhook test event")
        return {"status": "ok"}

    event_adapter = TypeAdapter(DailyWebhookEventUnion)
    try:
        event = event_adapter.validate_python(body_json)
    except Exception as e:
        logger.error("Failed to parse webhook event", error=str(e), body=body.decode())
        raise HTTPException(status_code=422, detail="Invalid event format")

    match event:
        case ParticipantJoinedEvent():
            await _handle_participant_joined(event)
        case ParticipantLeftEvent():
            await _handle_participant_left(event)
        case RecordingStartedEvent():
            await _handle_recording_started(event)
        case RecordingReadyEvent():
            await _handle_recording_ready(event)
        case RecordingErrorEvent():
            await _handle_recording_error(event)
        case _:
            assert_never(event)

    return {"status": "ok"}


async def _queue_poll_for_room(
    room_name: str | None,
    event_type: str,
    user_id: str | None,
    session_id: str | None,
    **log_kwargs,
) -> None:
    """Queue poll task for room by name, handling missing room/meeting cases."""
    if not room_name:
        logger.warning(f"{event_type}: no room in payload")
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if not meeting:
        logger.warning(f"{event_type}: meeting not found", room_name=room_name)
        return

    poll_daily_room_presence_task.delay(meeting.id)

    logger.info(
        f"{event_type.replace('.', ' ').title()} - poll queued",
        meeting_id=meeting.id,
        room_name=room_name,
        user_id=user_id,
        session_id=session_id,
        **log_kwargs,
    )


async def _handle_participant_joined(event: ParticipantJoinedEvent):
    """Queue poll task for presence reconciliation."""
    await _queue_poll_for_room(
        event.payload.room_name,
        "participant.joined",
        event.payload.user_id,
        event.payload.session_id,
        user_name=event.payload.user_name,
    )


async def _handle_participant_left(event: ParticipantLeftEvent):
    """Close session directly on webhook and update num_clients.

    The webhook IS the authoritative signal that a participant left.
    We close the session immediately rather than polling Daily.co API,
    which avoids the race where the API still shows the participant.
    A delayed reconciliation poll is queued as a safety net.
    """
    room_name = event.payload.room_name
    if not room_name:
        logger.warning("participant.left: no room in payload")
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if not meeting:
        logger.warning("participant.left: meeting not found", room_name=room_name)
        return

    log = logger.bind(
        meeting_id=meeting.id,
        room_name=room_name,
        session_id=event.payload.session_id,
        user_id=event.payload.user_id,
    )

    existing = await daily_participant_sessions_controller.get_open_session(
        meeting.id, event.payload.session_id
    )

    if existing:
        now = datetime.now(timezone.utc)
        await daily_participant_sessions_controller.batch_close_sessions(
            [existing.id], left_at=now
        )
        active = await daily_participant_sessions_controller.get_active_by_meeting(
            meeting.id
        )
        await meetings_controller.update_meeting(meeting.id, num_clients=len(active))
        log.info(
            "Participant left - session closed",
            remaining_clients=len(active),
            duration=event.payload.duration,
        )
    else:
        log.info(
            "Participant left - no open session found, skipping direct close",
            duration=event.payload.duration,
        )

    # Delayed reconciliation poll as safety net
    poll_daily_room_presence_task.apply_async(args=[meeting.id], countdown=5)


async def _handle_recording_started(event: RecordingStartedEvent):
    room_name = event.payload.room_name
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
            recording_id=event.payload.recording_id,
            platform="daily",
        )
    else:
        logger.warning("recording.started: meeting not found", room_name=room_name)


async def _handle_recording_ready(event: RecordingReadyEvent):
    room_name = event.payload.room_name
    recording_id = event.payload.recording_id
    recording_type = event.payload.type

    logger.info(
        "Recording ready for download",
        room_name=room_name,
        recording_id=recording_id,
        recording_type=recording_type,
        platform="daily",
    )

    bucket_name = settings.DAILYCO_STORAGE_AWS_BUCKET_NAME
    if not bucket_name:
        logger.error("DAILYCO_STORAGE_AWS_BUCKET_NAME not configured")
        return

    if recording_type == "cloud":
        await store_cloud_recording(
            recording_id=recording_id,
            room_name=room_name,
            s3_key=event.payload.s3_key,
            duration=event.payload.duration,
            start_ts=event.payload.start_ts,
            source="webhook",
        )

    elif recording_type == "raw-tracks":
        tracks = event.payload.tracks
        if not tracks:
            logger.warning(
                "raw-tracks recording: missing tracks array",
                room_name=room_name,
                recording_id=recording_id,
            )
            return

        track_keys = [t.s3Key for t in tracks if t.type == "audio"]

        logger.info(
            "Raw-tracks recording queuing processing",
            recording_id=recording_id,
            room_name=room_name,
            num_tracks=len(track_keys),
        )

        process_multitrack_recording.delay(
            bucket_name=bucket_name,
            daily_room_name=room_name,
            recording_id=recording_id,
            track_keys=track_keys,
            recording_start_ts=event.payload.start_ts,
        )

    else:
        logger.warning(
            "Unknown recording type",
            recording_type=recording_type,
            recording_id=recording_id,
        )


async def _handle_recording_error(event: RecordingErrorEvent):
    payload = event.payload
    room_name = payload.room_name

    meeting = await meetings_controller.get_by_room_name(room_name)
    if meeting:
        logger.error(
            "Recording error",
            meeting_id=meeting.id,
            room_name=room_name,
            error=payload.error_msg,
            platform="daily",
        )
    else:
        logger.warning("recording.error: meeting not found", room_name=room_name)
