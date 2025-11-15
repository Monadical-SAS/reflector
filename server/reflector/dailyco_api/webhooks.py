"""
Daily.co Webhook Event Models

Reference: https://docs.daily.co/reference/rest-api/webhooks
"""

from typing import Any, Dict, Literal

from pydantic import BaseModel, Field


class DailyTrack(BaseModel):
    """
    Individual audio or video track from a multitrack recording.

    Reference: https://docs.daily.co/reference/rest-api/recordings/raw-tracks-recordings
    """

    type: Literal["audio", "video"]
    s3Key: str = Field(description="S3 object key for the track file")
    size: int = Field(description="File size in bytes")


class DailyWebhookEvent(BaseModel):
    """
    Base structure for all Daily.co webhook events.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/webhook-payload
    """

    version: str = Field(description="Webhook payload version (e.g., '1.0.0')")
    type: str = Field(
        description="Event type (e.g., 'participant.joined', 'recording.ready-to-download')"
    )
    id: str = Field(description="Unique event identifier")
    payload: Dict[str, Any] = Field(description="Event-specific payload data")
    event_ts: float = Field(description="Event timestamp in Unix epoch seconds")


class ParticipantJoinedPayload(BaseModel):
    """
    Payload for participant.joined webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/participant-events
    """

    room: str | None = Field(None, description="Daily.co room name (older API)")
    room_name: str | None = Field(None, description="Daily.co room name")
    session_id: str = Field(description="Daily.co session identifier")
    user_id: str = Field(description="User identifier (may be encoded)")
    user_name: str | None = Field(None, description="User display name")
    joined_at: float = Field(description="Join timestamp in Unix epoch seconds")


class ParticipantLeftPayload(BaseModel):
    """
    Payload for participant.left webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/participant-events
    """

    room: str | None = Field(None, description="Daily.co room name (older API)")
    room_name: str | None = Field(None, description="Daily.co room name")
    session_id: str = Field(description="Daily.co session identifier")
    user_id: str = Field(description="User identifier (may be encoded)")
    user_name: str | None = Field(None, description="User display name")
    joined_at: float = Field(description="Join timestamp in Unix epoch seconds")
    duration: int | None = Field(
        None, description="Duration of participation in seconds"
    )


class RecordingStartedPayload(BaseModel):
    """
    Payload for recording.started webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/recording-events
    """

    room: str | None = Field(None, description="Daily.co room name (older API)")
    room_name: str | None = Field(None, description="Daily.co room name")
    recording_id: str = Field(description="Recording identifier")
    start_ts: float | None = Field(None, description="Recording start timestamp")


class RecordingReadyToDownloadPayload(BaseModel):
    """
    Payload for recording.ready-to-download webhook event.
    This is sent when raw-tracks recordings are complete and uploaded to S3.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/recording-events
    Reference: https://docs.daily.co/reference/rest-api/recordings/raw-tracks-recordings
    """

    room: str | None = Field(None, description="Daily.co room name (older API)")
    room_name: str | None = Field(None, description="Daily.co room name")
    recording_id: str = Field(description="Recording identifier")
    start_ts: float | None = Field(None, description="Recording start timestamp")
    status: str = Field(description="Recording status (e.g., 'finished')")
    max_participants: int | None = Field(
        None, description="Maximum participants during recording"
    )
    duration: int | None = Field(None, description="Recording duration in seconds")
    share_token: str | None = Field(None, description="Token for sharing recording")
    s3_key: str | None = Field(
        None, description="S3 prefix for single-track recordings (deprecated)"
    )
    tracks: list[DailyTrack] | None = Field(
        None, description="Array of audio/video tracks for multitrack recordings"
    )


class RecordingErrorPayload(BaseModel):
    """
    Payload for recording.error webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/recording-events
    """

    room: str | None = Field(None, description="Daily.co room name (older API)")
    room_name: str | None = Field(None, description="Daily.co room name")
    recording_id: str | None = Field(None, description="Recording identifier")
    error: str = Field(description="Error message describing what went wrong")
