"""
Daily.co API Request Models

Reference: https://docs.daily.co/reference/rest-api
"""

from typing import List, Literal

from pydantic import BaseModel, Field

from reflector.utils.string import NonEmptyString


class RecordingsBucketConfig(BaseModel):
    """
    S3 bucket configuration for raw-tracks recordings.

    Reference: https://docs.daily.co/reference/rest-api/rooms/create-room
    """

    bucket_name: NonEmptyString = Field(description="S3 bucket name")
    bucket_region: NonEmptyString = Field(description="AWS region (e.g., 'us-east-1')")
    assume_role_arn: NonEmptyString = Field(
        description="AWS IAM role ARN that Daily.co will assume to write recordings"
    )
    allow_api_access: bool = Field(
        default=True,
        description="Whether to allow API access to recording metadata",
    )


class RoomProperties(BaseModel):
    """
    Room configuration properties.
    """

    enable_recording: Literal["cloud", "local", "raw-tracks"] | None = Field(
        default=None,
        description="Recording mode: 'cloud' for mixed, 'local' for local recording, 'raw-tracks' for multitrack, None to disable",
    )
    enable_chat: bool = Field(default=True, description="Enable in-meeting chat")
    enable_screenshare: bool = Field(default=True, description="Enable screen sharing")
    enable_knocking: bool = Field(
        default=False,
        description="Enable knocking for private rooms (allows participants to request access)",
    )
    start_video_off: bool = Field(
        default=False, description="Start with video off for all participants"
    )
    start_audio_off: bool = Field(
        default=False, description="Start with audio muted for all participants"
    )
    exp: int | None = Field(
        None, description="Room expiration timestamp (Unix epoch seconds)"
    )
    recordings_bucket: RecordingsBucketConfig | None = Field(
        None, description="S3 bucket configuration for raw-tracks recordings"
    )


class CreateRoomRequest(BaseModel):
    """
    Request to create a new Daily.co room.

    Reference: https://docs.daily.co/reference/rest-api/rooms/create-room
    """

    name: NonEmptyString = Field(description="Room name (must be unique within domain)")
    privacy: Literal["public", "private"] = Field(
        default="public", description="Room privacy setting"
    )
    properties: RoomProperties = Field(
        default_factory=RoomProperties, description="Room configuration properties"
    )


class MeetingTokenProperties(BaseModel):
    """
    Properties for meeting token creation.

    Reference: https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token
    """

    room_name: NonEmptyString = Field(description="Room name this token is valid for")
    user_id: NonEmptyString | None = Field(
        None, description="User identifier to associate with token"
    )
    is_owner: bool = Field(
        default=False, description="Grant owner privileges to token holder"
    )
    start_cloud_recording: bool = Field(
        default=False, description="Automatically start cloud recording on join"
    )
    enable_recording_ui: bool = Field(
        default=True, description="Show recording controls in UI"
    )
    eject_at_token_exp: bool = Field(
        default=False, description="Eject participant when token expires"
    )
    nbf: int | None = Field(
        None, description="Not-before timestamp (Unix epoch seconds)"
    )
    exp: int | None = Field(
        None, description="Expiration timestamp (Unix epoch seconds)"
    )


class CreateMeetingTokenRequest(BaseModel):
    """
    Request to create a meeting token for participant authentication.

    Reference: https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token
    """

    properties: MeetingTokenProperties = Field(description="Token properties")


class CreateWebhookRequest(BaseModel):
    """
    Request to create a webhook subscription.

    Reference: https://docs.daily.co/reference/rest-api/webhooks
    """

    url: NonEmptyString = Field(description="Webhook endpoint URL (must be HTTPS)")
    eventTypes: List[
        Literal[
            "participant.joined",
            "participant.left",
            "recording.started",
            "recording.ready-to-download",
            "recording.error",
        ]
    ] = Field(
        description="Array of event types to subscribe to (only events we handle)"
    )
    hmac: NonEmptyString = Field(
        description="Base64-encoded HMAC secret for webhook signature verification"
    )
    basicAuth: NonEmptyString | None = Field(
        None, description="Optional basic auth credentials for webhook endpoint"
    )


class UpdateWebhookRequest(BaseModel):
    """
    Request to update an existing webhook.

    Note: Daily.co API may not support PATCH for webhooks.
    Common pattern is to delete and recreate.

    Reference: https://docs.daily.co/reference/rest-api/webhooks
    """

    url: NonEmptyString | None = Field(None, description="New webhook endpoint URL")
    eventTypes: List[NonEmptyString] | None = Field(
        None, description="New array of event types"
    )
    hmac: NonEmptyString | None = Field(None, description="New HMAC secret")
    basicAuth: NonEmptyString | None = Field(
        None, description="New basic auth credentials"
    )
