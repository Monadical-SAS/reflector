"""
Daily.co API Response Models

Reference: https://docs.daily.co/reference/rest-api
"""

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field


class RoomResponse(BaseModel):
    """
    Response from room creation or retrieval.

    Reference: https://docs.daily.co/reference/rest-api/rooms/create-room
    Reference: https://docs.daily.co/reference/rest-api/rooms/get-room-configuration
    """

    id: str = Field(description="Unique room identifier (UUID)")
    name: str = Field(description="Room name used in URLs")
    api_created: bool = Field(description="Whether room was created via API")
    privacy: Literal["public", "private"] = Field(description="Room privacy setting")
    url: str = Field(description="Full room URL")
    created_at: str = Field(description="ISO 8601 creation timestamp")
    config: Dict[str, Any] = Field(
        default_factory=dict, description="Room configuration properties"
    )


class RoomPresenceParticipant(BaseModel):
    """
    Participant presence information in a room.

    Reference: https://docs.daily.co/reference/rest-api/rooms/get-room-presence
    """

    room: str = Field(description="Room name")
    id: str = Field(description="Participant session ID")
    userId: str | None = Field(None, description="User ID if provided")
    userName: str | None = Field(None, description="User display name")
    joinTime: str = Field(description="ISO 8601 join timestamp")
    duration: int = Field(description="Duration in room (seconds)")


class RoomPresenceResponse(BaseModel):
    """
    Response from room presence endpoint.

    Reference: https://docs.daily.co/reference/rest-api/rooms/get-room-presence
    """

    total_count: int = Field(
        description="Total number of participants currently in room"
    )
    data: List[RoomPresenceParticipant] = Field(
        default_factory=list, description="Array of participant presence data"
    )


class MeetingParticipant(BaseModel):
    """
    Historical participant data from a meeting.

    Reference: https://docs.daily.co/reference/rest-api/meetings/get-meeting-participants
    """

    user_id: str = Field(description="User identifier")
    participant_id: str = Field(description="Participant session identifier")
    user_name: str | None = Field(None, description="User display name")
    join_time: int = Field(description="Join timestamp (Unix epoch seconds)")
    duration: int = Field(description="Duration in meeting (seconds)")


class MeetingParticipantsResponse(BaseModel):
    """
    Response from meeting participants endpoint.

    Reference: https://docs.daily.co/reference/rest-api/meetings/get-meeting-participants
    """

    data: List[MeetingParticipant] = Field(
        default_factory=list, description="Array of participant data"
    )


class MeetingResponse(BaseModel):
    """
    Response from meeting information endpoint.

    Reference: https://docs.daily.co/reference/rest-api/meetings/get-meeting-information
    """

    id: str = Field(description="Meeting session identifier (UUID)")
    room: str = Field(description="Room name where meeting occurred")
    start_time: int = Field(
        description="Meeting start Unix timestamp (~15s granularity)"
    )
    duration: int = Field(description="Total meeting duration in seconds")
    ongoing: bool = Field(description="Whether meeting is currently active")
    max_participants: int = Field(description="Peak concurrent participant count")
    participants: List[MeetingParticipant] = Field(
        default_factory=list, description="Array of participant session data"
    )


class RecordingS3Info(BaseModel):
    """
    S3 bucket information for a recording.

    Reference: https://docs.daily.co/reference/rest-api/recordings
    """

    bucket_name: str
    bucket_region: str
    endpoint: str | None = None


class RecordingResponse(BaseModel):
    """
    Response from recording retrieval endpoint.

    Reference: https://docs.daily.co/reference/rest-api/recordings/get-recording-info
    """

    id: str = Field(description="Recording identifier")
    room_name: str = Field(description="Room where recording occurred")
    start_ts: int = Field(description="Recording start timestamp (Unix epoch seconds)")
    status: str = Field(description="Recording status (e.g., 'finished', 'processing')")
    max_participants: int = Field(description="Maximum participants during recording")
    duration: int = Field(description="Recording duration in seconds")
    share_token: str | None = Field(None, description="Token for sharing recording")
    s3: RecordingS3Info | None = Field(None, description="S3 bucket information")


class MeetingTokenResponse(BaseModel):
    """
    Response from meeting token creation.

    Reference: https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token
    """

    token: str = Field(description="JWT meeting token for participant authentication")


class WebhookResponse(BaseModel):
    """
    Response from webhook creation or retrieval.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/create-webhook
    Reference: https://docs.daily.co/reference/rest-api/webhooks/list-webhooks
    """

    uuid: str = Field(description="Unique webhook identifier")
    url: str = Field(description="Webhook endpoint URL")
    hmac: str | None = Field(
        None, description="Base64-encoded HMAC secret for signature verification"
    )
    basicAuth: str | None = Field(
        None, description="Basic auth credentials if configured"
    )
    eventTypes: List[str] = Field(
        default_factory=list,
        description="Array of event types (e.g., ['recording.started', 'participant.joined'])",
    )
    state: Literal["ACTIVE", "FAILED"] = Field(
        description="Webhook state - FAILED after 3+ consecutive failures"
    )
    failedCount: int = Field(default=0, description="Number of consecutive failures")
    lastMomentPushed: str | None = Field(
        None, description="ISO 8601 timestamp of last successful push"
    )
    domainId: str = Field(description="Daily.co domain/account identifier")
    createdAt: str = Field(description="ISO 8601 creation timestamp")
    updatedAt: str = Field(description="ISO 8601 last update timestamp")
