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
from reflector.db import get_database
from reflector.db.daily_participant_sessions import (
    DailyParticipantSession,
    daily_participant_sessions_controller,
)
from reflector.db.meetings import meetings_controller
from reflector.logger import logger as _logger
from reflector.settings import settings
from reflector.video_platforms.factory import create_platform_client
from reflector.worker.process import process_multitrack_recording

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


async def _handle_participant_joined(event: ParticipantJoinedEvent):
    daily_room_name = event.payload.room_name
    if not daily_room_name:
        logger.warning("participant.joined: no room in payload", payload=event.payload)
        return

    meeting = await meetings_controller.get_by_room_name(daily_room_name)
    if not meeting:
        logger.warning(
            "participant.joined: meeting not found", room_name=daily_room_name
        )
        return

    payload = event.payload
    joined_at = datetime.fromtimestamp(payload.joined_at, tz=timezone.utc)
    session_id = f"{meeting.id}:{payload.session_id}"

    session = DailyParticipantSession(
        id=session_id,
        meeting_id=meeting.id,
        room_id=meeting.room_id,
        session_id=payload.session_id,
        user_id=payload.user_id,
        user_name=payload.user_name,
        joined_at=joined_at,
        left_at=None,
    )

    # num_clients serves as a projection/cache of active session count for Daily.co
    # Both operations must succeed or fail together to maintain consistency
    async with get_database().transaction():
        await meetings_controller.increment_num_clients(meeting.id)
        await daily_participant_sessions_controller.upsert_joined(session)

    logger.info(
        "Participant joined",
        meeting_id=meeting.id,
        room_name=daily_room_name,
        user_id=payload.user_id,
        user_name=payload.user_name,
        session_id=session_id,
    )


async def _handle_participant_left(event: ParticipantLeftEvent):
    room_name = event.payload.room_name
    if not room_name:
        logger.warning("participant.left: no room in payload", payload=event.payload)
        return

    meeting = await meetings_controller.get_by_room_name(room_name)
    if not meeting:
        logger.warning("participant.left: meeting not found", room_name=room_name)
        return

    payload = event.payload
    joined_at = datetime.fromtimestamp(payload.joined_at, tz=timezone.utc)
    left_at = datetime.fromtimestamp(event.event_ts, tz=timezone.utc)
    session_id = f"{meeting.id}:{payload.session_id}"

    session = DailyParticipantSession(
        id=session_id,
        meeting_id=meeting.id,
        room_id=meeting.room_id,
        session_id=payload.session_id,
        user_id=payload.user_id,
        user_name=payload.user_name,
        joined_at=joined_at,
        left_at=left_at,
    )

    # num_clients serves as a projection/cache of active session count for Daily.co
    # Both operations must succeed or fail together to maintain consistency
    async with get_database().transaction():
        await meetings_controller.decrement_num_clients(meeting.id)
        await daily_participant_sessions_controller.upsert_left(session)

    logger.info(
        "Participant left",
        meeting_id=meeting.id,
        room_name=room_name,
        user_id=payload.user_id,
        duration=payload.duration,
        session_id=session_id,
    )


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
    tracks = event.payload.tracks

    if not tracks:
        logger.warning(
            "recording.ready-to-download: missing tracks",
            room_name=room_name,
            recording_id=recording_id,
            payload=event.payload,
        )
        return

    logger.info(
        "Recording ready for download",
        room_name=room_name,
        recording_id=recording_id,
        num_tracks=len(tracks),
        platform="daily",
    )

    bucket_name = settings.DAILYCO_STORAGE_AWS_BUCKET_NAME
    if not bucket_name:
        logger.error(
            "DAILYCO_STORAGE_AWS_BUCKET_NAME not configured; cannot process Daily recording"
        )
        return

    track_keys = [t.s3Key for t in tracks if t.type == "audio"]

    logger.info(
        "Recording webhook queuing processing",
        recording_id=recording_id,
        room_name=room_name,
    )

    process_multitrack_recording.delay(
        bucket_name=bucket_name,
        daily_room_name=room_name,
        recording_id=recording_id,
        track_keys=track_keys,
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
