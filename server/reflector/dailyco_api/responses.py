"""
Daily.co API Response Models
"""

from typing import Any, Dict, List, Literal

from pydantic import BaseModel, Field

from reflector.dailyco_api.webhooks import DailyTrack
from reflector.utils.string import NonEmptyString

# not documented in daily; we fill it according to observations
RecordingStatus = Literal["in-progress", "finished"]


class RoomResponse(BaseModel):
    """
    Response from room creation or retrieval.

    Reference: https://docs.daily.co/reference/rest-api/rooms/create-room
    """

    id: NonEmptyString = Field(description="Unique room identifier (UUID)")
    name: NonEmptyString = Field(description="Room name used in URLs")
    api_created: bool = Field(description="Whether room was created via API")
    privacy: Literal["public", "private"] = Field(description="Room privacy setting")
    url: NonEmptyString = Field(description="Full room URL")
    created_at: NonEmptyString = Field(description="ISO 8601 creation timestamp")
    config: Dict[NonEmptyString, Any] = Field(
        default_factory=dict, description="Room configuration properties"
    )


class RoomPresenceParticipant(BaseModel):
    """
    Participant presence information in a room.

    Reference: https://docs.daily.co/reference/rest-api/rooms/get-room-presence
    """

    room: NonEmptyString = Field(description="Room name")
    id: NonEmptyString = Field(description="Participant session ID")
    userId: NonEmptyString | None = Field(None, description="User ID if provided")
    userName: NonEmptyString | None = Field(None, description="User display name")
    joinTime: NonEmptyString = Field(description="ISO 8601 join timestamp")
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

    user_id: NonEmptyString | None = Field(None, description="User identifier")
    participant_id: NonEmptyString = Field(description="Participant session identifier")
    user_name: NonEmptyString | None = Field(None, description="User display name")
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

    id: NonEmptyString = Field(description="Meeting session identifier (UUID)")
    room: NonEmptyString = Field(description="Room name where meeting occurred")
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

    bucket_name: NonEmptyString
    bucket_region: NonEmptyString
    key: NonEmptyString | None = None
    endpoint: NonEmptyString | None = None


class RecordingResponse(BaseModel):
    """
    Response from recording retrieval endpoint (network layer).

    Duration may be None for recordings still being processed by Daily.
    Use FinishedRecordingResponse for recordings ready for processing.

    Reference: https://docs.daily.co/reference/rest-api/recordings
    """

    id: NonEmptyString = Field(description="Recording identifier")
    room_name: NonEmptyString = Field(description="Room where recording occurred")
    start_ts: int = Field(description="Recording start timestamp (Unix epoch seconds)")
    type: Literal["cloud", "raw-tracks"] | None = Field(
        None, description="Recording type (may be missing from API)"
    )
    status: RecordingStatus = Field(
        description="Recording status ('in-progress' or 'finished')"
    )
    max_participants: int | None = Field(
        None, description="Maximum participants during recording (may be missing)"
    )
    duration: int | None = Field(
        None, description="Recording duration in seconds (None if still processing)"
    )
    share_token: NonEmptyString | None = Field(
        None, description="Token for sharing recording"
    )
    s3: RecordingS3Info | None = Field(None, description="S3 bucket information")
    s3key: NonEmptyString | None = Field(
        None, description="S3 key for cloud recordings (top-level field)"
    )
    tracks: list[DailyTrack] = Field(
        default_factory=list,
        description="Track list for raw-tracks recordings (always array, never null)",
    )
    # this is not a mistake but a deliberate Daily.co naming decision
    mtgSessionId: NonEmptyString | None = Field(
        None, description="Meeting session identifier (may be missing)"
    )

    def to_finished(self) -> "FinishedRecordingResponse | None":
        """Convert to FinishedRecordingResponse if duration is available and status is finished."""
        if self.duration is None or self.status != "finished":
            return None
        return FinishedRecordingResponse(**self.model_dump())


class FinishedRecordingResponse(RecordingResponse):
    """
    Recording with confirmed duration - ready for processing.

    This model guarantees duration is present and status is finished.
    """

    status: Literal["finished"] = Field(
        description="Recording status (always 'finished')"
    )
    duration: int = Field(description="Recording duration in seconds")


class MeetingTokenResponse(BaseModel):
    """
    Response from meeting token creation.

    Reference: https://docs.daily.co/reference/rest-api/meeting-tokens/create-meeting-token
    """

    token: NonEmptyString = Field(
        description="JWT meeting token for participant authentication"
    )


class WebhookResponse(BaseModel):
    """
    Response from webhook creation or retrieval.

    Reference: https://docs.daily.co/reference/rest-api/webhooks
    """

    uuid: NonEmptyString = Field(description="Unique webhook identifier")
    url: NonEmptyString = Field(description="Webhook endpoint URL")
    hmac: NonEmptyString | None = Field(
        None, description="Base64-encoded HMAC secret for signature verification"
    )
    basicAuth: NonEmptyString | None = Field(
        None, description="Basic auth credentials if configured"
    )
    eventTypes: List[NonEmptyString] = Field(
        default_factory=list,
        description="Array of event types (e.g., ['recording.started', 'participant.joined'])",
    )
    state: Literal["ACTIVE", "FAILED"] = Field(
        description="Webhook state - FAILED after 3+ consecutive failures"
    )
    failedCount: int = Field(default=0, description="Number of consecutive failures")
    lastMomentPushed: NonEmptyString | None = Field(
        None, description="ISO 8601 timestamp of last successful push"
    )
    domainId: NonEmptyString = Field(description="Daily.co domain/account identifier")
    createdAt: NonEmptyString = Field(description="ISO 8601 creation timestamp")
    updatedAt: NonEmptyString = Field(description="ISO 8601 last update timestamp")
