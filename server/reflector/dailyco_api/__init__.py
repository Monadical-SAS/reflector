"""
Daily.co API Module
"""

# Client
from .client import DailyApiClient, DailyApiError

# Request models
from .requests import (
    CreateMeetingTokenRequest,
    CreateRoomRequest,
    CreateWebhookRequest,
    MeetingTokenProperties,
    RecordingsBucketConfig,
    RoomProperties,
    UpdateWebhookRequest,
)

# Response models
from .responses import (
    MeetingParticipant,
    MeetingParticipantsResponse,
    MeetingResponse,
    MeetingTokenResponse,
    RecordingResponse,
    RecordingS3Info,
    RoomPresenceParticipant,
    RoomPresenceResponse,
    RoomResponse,
    WebhookResponse,
)

# Webhook utilities
from .webhook_utils import (
    extract_room_name,
    parse_participant_joined,
    parse_participant_left,
    parse_recording_error,
    parse_recording_ready,
    parse_recording_started,
    parse_webhook_payload,
    verify_webhook_signature,
)

# Webhook models
from .webhooks import (
    DailyTrack,
    DailyWebhookEvent,
    ParticipantJoinedPayload,
    ParticipantLeftPayload,
    RecordingErrorPayload,
    RecordingReadyToDownloadPayload,
    RecordingStartedPayload,
)

__all__ = [
    # Client
    "DailyApiClient",
    "DailyApiError",
    # Requests
    "CreateRoomRequest",
    "RoomProperties",
    "RecordingsBucketConfig",
    "CreateMeetingTokenRequest",
    "MeetingTokenProperties",
    "CreateWebhookRequest",
    "UpdateWebhookRequest",
    # Responses
    "RoomResponse",
    "RoomPresenceResponse",
    "RoomPresenceParticipant",
    "MeetingParticipantsResponse",
    "MeetingParticipant",
    "MeetingResponse",
    "RecordingResponse",
    "RecordingS3Info",
    "MeetingTokenResponse",
    "WebhookResponse",
    # Webhooks
    "DailyWebhookEvent",
    "DailyTrack",
    "ParticipantJoinedPayload",
    "ParticipantLeftPayload",
    "RecordingStartedPayload",
    "RecordingReadyToDownloadPayload",
    "RecordingErrorPayload",
    # Webhook utilities
    "verify_webhook_signature",
    "extract_room_name",
    "parse_webhook_payload",
    "parse_participant_joined",
    "parse_participant_left",
    "parse_recording_started",
    "parse_recording_ready",
    "parse_recording_error",
]
