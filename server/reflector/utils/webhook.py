"""Webhook utilities.

Shared webhook functionality for both Hatchet and Celery pipelines.
"""

import hashlib
import hmac
import uuid
from datetime import datetime, timezone

import httpx
from pydantic import BaseModel

from reflector.logger import logger
from reflector.settings import settings
from reflector.utils.string import NonEmptyString
from reflector.utils.webhook_outgoing_models import (
    WebhookCalendarEventPayload,
    WebhookParticipantPayload,
    WebhookPayload,
    WebhookRoomPayload,
    WebhookTestPayload,
    WebhookTopicPayload,
    WebhookTranscriptPayload,
)

__all__ = [
    "build_transcript_webhook_payload",
    "build_test_webhook_payload",
    "build_webhook_headers",
    "generate_webhook_signature",
    "send_webhook_request",
]


def _serialize_payload(payload: BaseModel) -> bytes:
    """Serialize Pydantic model to compact JSON bytes."""
    return payload.model_dump_json(by_alias=True, exclude_none=False).encode("utf-8")


def generate_webhook_signature(payload: bytes, secret: str, timestamp: str) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
    signed_payload = f"{timestamp}.{payload.decode('utf-8')}"
    hmac_obj = hmac.new(
        secret.encode("utf-8"),
        signed_payload.encode("utf-8"),
        hashlib.sha256,
    )
    return hmac_obj.hexdigest()


def build_webhook_headers(
    event_type: str,
    payload_bytes: bytes,
    webhook_secret: str | None = None,
    retry_count: int = 0,
) -> dict[str, str]:
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "Reflector-Webhook/1.0",
        "X-Webhook-Event": event_type,
        "X-Webhook-Retry": str(retry_count),
    }

    if webhook_secret:
        timestamp = str(int(datetime.now(timezone.utc).timestamp()))
        signature = generate_webhook_signature(payload_bytes, webhook_secret, timestamp)
        headers["X-Webhook-Signature"] = f"t={timestamp},v1={signature}"

    return headers


async def send_webhook_request(
    url: str,
    payload: BaseModel,
    event_type: str,
    webhook_secret: str | None = None,
    retry_count: int = 0,
    timeout: float = 30.0,
) -> httpx.Response:
    """Send webhook request with proper headers and signature.

    Raises:
        httpx.HTTPStatusError: On non-2xx response
        httpx.ConnectError: On connection failure
        httpx.TimeoutException: On timeout
    """
    payload_bytes = _serialize_payload(payload)

    headers = build_webhook_headers(
        event_type=event_type,
        payload_bytes=payload_bytes,
        webhook_secret=webhook_secret,
        retry_count=retry_count,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(url, content=payload_bytes, headers=headers)
        response.raise_for_status()
        return response


async def build_transcript_webhook_payload(
    transcript_id: NonEmptyString,
    room_id: NonEmptyString,
) -> WebhookPayload | None:
    """Build webhook payload by fetching transcript and room data from database."""
    # Inline imports required: this utils module would create circular imports
    # if db modules were imported at top level (utils -> db -> ... -> utils).
    # This pattern is consistent with Hatchet task files.
    from reflector.db.calendar_events import calendar_events_controller  # noqa: PLC0415
    from reflector.db.meetings import meetings_controller  # noqa: PLC0415
    from reflector.db.rooms import rooms_controller  # noqa: PLC0415
    from reflector.db.transcripts import transcripts_controller  # noqa: PLC0415
    from reflector.utils.webvtt import topics_to_webvtt  # noqa: PLC0415

    transcript = await transcripts_controller.get_by_id(transcript_id)
    if not transcript:
        return None

    room = await rooms_controller.get_by_id(room_id)
    if not room:
        return None

    topics_data = [
        WebhookTopicPayload(
            title=topic.title,
            summary=topic.summary,
            timestamp=topic.timestamp,
            duration=topic.duration,
            webvtt=topics_to_webvtt([topic]) if topic.words else "",
        )
        for topic in (transcript.topics or [])
    ]

    participants_data = [
        WebhookParticipantPayload(id=p.id, name=p.name, speaker=p.speaker)
        for p in (transcript.participants or [])
    ]

    calendar_event_data: WebhookCalendarEventPayload | None = None
    try:
        if transcript.meeting_id:
            meeting = await meetings_controller.get_by_id(transcript.meeting_id)
            if meeting and meeting.calendar_event_id:
                calendar_event = await calendar_events_controller.get_by_id(
                    meeting.calendar_event_id
                )
                if calendar_event:
                    calendar_event_data = WebhookCalendarEventPayload(
                        id=calendar_event.id,
                        ics_uid=calendar_event.ics_uid,
                        title=calendar_event.title,
                        start_time=calendar_event.start_time,
                        end_time=calendar_event.end_time,
                        description=calendar_event.description or None,
                        location=calendar_event.location or None,
                        attendees=calendar_event.attendees or None,
                    )
    except Exception as e:
        logger.warning(
            "Failed to fetch calendar event for webhook",
            transcript_id=transcript_id,
            meeting_id=transcript.meeting_id,
            error=str(e),
        )

    frontend_url = f"{settings.UI_BASE_URL}/transcripts/{transcript.id}"

    return WebhookPayload(
        event="transcript.completed",
        event_id=uuid.uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        transcript=WebhookTranscriptPayload(
            id=transcript.id,
            room_id=transcript.room_id,
            created_at=transcript.created_at,
            duration=transcript.duration,
            title=transcript.title,
            short_summary=transcript.short_summary,
            long_summary=transcript.long_summary,
            webvtt=transcript.webvtt,
            topics=topics_data,
            participants=participants_data,
            source_language=transcript.source_language,
            target_language=transcript.target_language,
            status=transcript.status,
            frontend_url=frontend_url,
            action_items=transcript.action_items,
        ),
        room=WebhookRoomPayload(
            id=room.id,
            name=room.name,
        ),
        calendar_event=calendar_event_data,
    )


async def build_test_webhook_payload(
    room_id: NonEmptyString,
) -> WebhookTestPayload | None:
    """Build test webhook payload."""
    # Inline import: avoid circular dependency (utils -> db -> utils)
    from reflector.db.rooms import rooms_controller  # noqa: PLC0415

    room = await rooms_controller.get_by_id(room_id)
    if not room:
        return None

    return WebhookTestPayload(
        event="test",
        event_id=uuid.uuid4().hex,
        timestamp=datetime.now(timezone.utc),
        message="This is a test webhook from Reflector",
        room=WebhookRoomPayload(
            id=room.id,
            name=room.name,
        ),
    )
