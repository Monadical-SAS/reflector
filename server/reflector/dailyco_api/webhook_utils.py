"""
Daily.co Webhook Utilities

Utilities for verifying and parsing Daily.co webhook events.

Reference: https://docs.daily.co/reference/rest-api/webhooks
"""

import base64
import hmac
from hashlib import sha256

import structlog

from .webhooks import (
    DailyWebhookEvent,
    ParticipantJoinedPayload,
    ParticipantLeftPayload,
    RecordingErrorPayload,
    RecordingReadyToDownloadPayload,
    RecordingStartedPayload,
)

logger = structlog.get_logger(__name__)


def verify_webhook_signature(
    body: bytes,
    signature: str,
    timestamp: str,
    webhook_secret: str,
) -> bool:
    """
    Verify Daily.co webhook signature using HMAC-SHA256.

    Daily.co signature verification:
    1. Base64-decode the webhook secret
    2. Create signed content: timestamp + '.' + body
    3. Compute HMAC-SHA256(secret, signed_content)
    4. Base64-encode the result
    5. Compare with provided signature using constant-time comparison

    Reference: https://docs.daily.co/reference/rest-api/webhooks

    Args:
        body: Raw request body bytes
        signature: X-Webhook-Signature header value
        timestamp: X-Webhook-Timestamp header value
        webhook_secret: Base64-encoded HMAC secret

    Returns:
        True if signature is valid, False otherwise

    Example:
        >>> body = b'{"version":"1.0.0","type":"participant.joined",...}'
        >>> signature = "abc123..."
        >>> timestamp = "1234567890"
        >>> secret = "your-base64-secret"
        >>> is_valid = verify_webhook_signature(body, signature, timestamp, secret)
    """
    if not signature or not timestamp or not webhook_secret:
        logger.warning(
            "Missing required data for webhook verification",
            has_signature=bool(signature),
            has_timestamp=bool(timestamp),
            has_secret=bool(webhook_secret),
        )
        return False

    try:
        secret_bytes = base64.b64decode(webhook_secret)
        signed_content = timestamp.encode() + b"." + body
        expected = hmac.new(secret_bytes, signed_content, sha256).digest()
        expected_b64 = base64.b64encode(expected).decode()

        # Constant-time comparison to prevent timing attacks
        return hmac.compare_digest(expected_b64, signature)

    except (base64.binascii.Error, ValueError, TypeError, UnicodeDecodeError) as e:
        logger.error(
            "Webhook signature verification failed",
            error=str(e),
            error_type=type(e).__name__,
        )
        return False


def extract_room_name(event: DailyWebhookEvent) -> str | None:
    """
    Extract room name from Daily.co webhook event payload.

    Args:
        event: Parsed webhook event

    Returns:
        Room name if present and is a string, None otherwise

    Example:
        >>> event = DailyWebhookEvent(**webhook_payload)
        >>> room_name = extract_room_name(event)
    """
    room = event.payload.get("room_name")
    # Ensure we return a string, not any falsy value that might be in payload
    return room if isinstance(room, str) else None


def parse_participant_joined(event: DailyWebhookEvent) -> ParticipantJoinedPayload:
    """
    Parse participant.joined webhook event payload.

    Args:
        event: Webhook event with type "participant.joined"

    Returns:
        Parsed participant joined payload

    Raises:
        pydantic.ValidationError: If payload doesn't match expected schema
    """
    return ParticipantJoinedPayload(**event.payload)


def parse_participant_left(event: DailyWebhookEvent) -> ParticipantLeftPayload:
    """
    Parse participant.left webhook event payload.

    Args:
        event: Webhook event with type "participant.left"

    Returns:
        Parsed participant left payload

    Raises:
        pydantic.ValidationError: If payload doesn't match expected schema
    """
    return ParticipantLeftPayload(**event.payload)


def parse_recording_started(event: DailyWebhookEvent) -> RecordingStartedPayload:
    """
    Parse recording.started webhook event payload.

    Args:
        event: Webhook event with type "recording.started"

    Returns:
        Parsed recording started payload

    Raises:
        pydantic.ValidationError: If payload doesn't match expected schema
    """
    return RecordingStartedPayload(**event.payload)


def parse_recording_ready(
    event: DailyWebhookEvent,
) -> RecordingReadyToDownloadPayload:
    """
    Parse recording.ready-to-download webhook event payload.

    This event is sent when raw-tracks recordings are complete and uploaded to S3.
    The payload includes a 'tracks' array with individual audio/video files.

    Args:
        event: Webhook event with type "recording.ready-to-download"

    Returns:
        Parsed recording ready payload with tracks array

    Raises:
        pydantic.ValidationError: If payload doesn't match expected schema

    Example:
        >>> event = DailyWebhookEvent(**webhook_payload)
        >>> if event.type == "recording.ready-to-download":
        ...     payload = parse_recording_ready(event)
        ...     audio_tracks = [t for t in payload.tracks if t.type == "audio"]
    """
    return RecordingReadyToDownloadPayload(**event.payload)


def parse_recording_error(event: DailyWebhookEvent) -> RecordingErrorPayload:
    """
    Parse recording.error webhook event payload.

    Args:
        event: Webhook event with type "recording.error"

    Returns:
        Parsed recording error payload

    Raises:
        pydantic.ValidationError: If payload doesn't match expected schema
    """
    return RecordingErrorPayload(**event.payload)


# Webhook event type to parser mapping
WEBHOOK_PARSERS = {
    "participant.joined": parse_participant_joined,
    "participant.left": parse_participant_left,
    "recording.started": parse_recording_started,
    "recording.ready-to-download": parse_recording_ready,
    "recording.error": parse_recording_error,
}


def parse_webhook_payload(event: DailyWebhookEvent):
    """
    Parse webhook event payload based on event type.

    Args:
        event: Webhook event

    Returns:
        Typed payload model based on event type, or raw dict if unknown

    Example:
        >>> event = DailyWebhookEvent(**webhook_payload)
        >>> payload = parse_webhook_payload(event)
        >>> if isinstance(payload, ParticipantJoinedPayload):
        ...     print(f"User {payload.user_name} joined")
    """
    parser = WEBHOOK_PARSERS.get(event.type)
    if parser:
        return parser(event)
    else:
        logger.warning("Unknown webhook event type", event_type=event.type)
        return event.payload
