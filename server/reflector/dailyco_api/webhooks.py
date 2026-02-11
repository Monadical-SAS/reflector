"""
Daily.co Webhook Event Models

Reference: https://docs.daily.co/reference/rest-api/webhooks
"""

from typing import Annotated, Any, Dict, Literal, Union

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

from reflector.utils.string import NonEmptyString


def normalize_timestamp_to_int(v):
    """
    Normalize float timestamps to int by truncating decimal part.

    Daily.co sometimes sends timestamps as floats (e.g., 1708972279.96).
    Pydantic expects int for fields typed as `int`.
    """
    if v is None:
        return v
    if isinstance(v, float):
        return int(v)
    return v


WebhookEventType = Literal[
    "participant.joined",
    "participant.left",
    "recording.started",
    "recording.ready-to-download",
    "recording.error",
]


class DailyTrack(BaseModel):
    """
    Individual audio or video track from a multitrack recording.

    Reference: https://docs.daily.co/reference/rest-api/recordings
    """

    model_config = ConfigDict(extra="ignore")

    type: Literal["audio", "video"]
    s3Key: NonEmptyString = Field(description="S3 object key for the track file")
    size: int = Field(description="File size in bytes")


class DailyWebhookEvent(BaseModel):
    """
    Base structure for all Daily.co webhook events.
    All events share five common fields documented below.

    Reference: https://docs.daily.co/reference/rest-api/webhooks
    """

    model_config = ConfigDict(extra="ignore")

    version: NonEmptyString = Field(
        description="Represents the version of the event. This uses semantic versioning to inform a consumer if the payload has introduced any breaking changes"
    )
    type: WebhookEventType = Field(
        description="Represents the type of the event described in the payload"
    )
    id: NonEmptyString = Field(
        description="An identifier representing this specific event"
    )
    payload: Dict[NonEmptyString, Any] = Field(
        description="An object representing the event, whose fields are described in the corresponding payload class"
    )
    event_ts: int = Field(
        description="Documenting when the webhook itself was sent. This timestamp is different than the time of the event the webhook describes. For example, a recording.started event will contain a start_ts timestamp of when the actual recording started, and a slightly later event_ts timestamp indicating when the webhook event was sent"
    )

    _normalize_event_ts = field_validator("event_ts", mode="before")(
        normalize_timestamp_to_int
    )


class ParticipantJoinedPayload(BaseModel):
    """
    Payload for participant.joined webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/events/participant-joined
    """

    model_config = ConfigDict(extra="ignore")

    room_name: NonEmptyString | None = Field(
        None,
        description="Daily.co room name",
        validation_alias=AliasChoices("room_name", "room"),
    )
    session_id: NonEmptyString = Field(description="Daily.co session identifier")
    user_id: NonEmptyString = Field(description="User identifier (may be encoded)")
    user_name: NonEmptyString | None = Field(None, description="User display name")
    joined_at: int = Field(description="Join timestamp in Unix epoch seconds")

    _normalize_joined_at = field_validator("joined_at", mode="before")(
        normalize_timestamp_to_int
    )


class ParticipantLeftPayload(BaseModel):
    """
    Payload for participant.left webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/events/participant-left
    """

    model_config = ConfigDict(extra="ignore")

    room_name: NonEmptyString | None = Field(
        None,
        description="Daily.co room name",
        validation_alias=AliasChoices("room_name", "room"),
    )
    session_id: NonEmptyString = Field(description="Daily.co session identifier")
    user_id: NonEmptyString = Field(description="User identifier (may be encoded)")
    user_name: NonEmptyString | None = Field(None, description="User display name")
    joined_at: int = Field(description="Join timestamp in Unix epoch seconds")
    duration: int | None = Field(
        None, description="Duration of participation in seconds"
    )

    _normalize_joined_at = field_validator("joined_at", mode="before")(
        normalize_timestamp_to_int
    )
    _normalize_duration = field_validator("duration", mode="before")(
        normalize_timestamp_to_int
    )


class RecordingStartedPayload(BaseModel):
    """
    Payload for recording.started webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/events/recording-started
    """

    model_config = ConfigDict(extra="ignore")

    room_name: NonEmptyString | None = Field(None, description="Daily.co room name")
    recording_id: NonEmptyString = Field(description="Recording identifier")
    start_ts: int | None = Field(None, description="Recording start timestamp")

    _normalize_start_ts = field_validator("start_ts", mode="before")(
        normalize_timestamp_to_int
    )


class RecordingReadyToDownloadPayload(BaseModel):
    """
    Payload for recording.ready-to-download webhook event.
    This is sent when raw-tracks recordings are complete and uploaded to S3.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/events/recording-ready-to-download
    """

    model_config = ConfigDict(extra="ignore")

    type: Literal["cloud", "cloud-audio-only", "raw-tracks"] = Field(
        description="The type of recording that was generated"
    )
    recording_id: NonEmptyString = Field(
        description="An ID identifying the recording that was generated"
    )
    room_name: NonEmptyString = Field(
        description="The name of the room where the recording was made"
    )
    start_ts: int = Field(
        description="The Unix epoch time in seconds representing when the recording started"
    )
    status: Literal["finished"] = Field(
        description="The status of the given recording (always 'finished' in ready-to-download webhook, see RecordingStatus in responses.py for full API statuses)"
    )
    max_participants: int | None = Field(
        None,
        description="The number of participants on the call that were recorded (optional; Daily may omit it in some webhook versions)",
    )
    duration: int = Field(description="The duration in seconds of the call")
    s3_key: NonEmptyString = Field(
        description="The location of the recording in the provided S3 bucket"
    )
    share_token: NonEmptyString | None = Field(
        None, description="undocumented documented secret field"
    )
    tracks: list[DailyTrack] | None = Field(
        None,
        description="If the recording is a raw-tracks recording, a tracks field will be provided. If role permissions have been removed, the tracks field may be null",
    )

    _normalize_start_ts = field_validator("start_ts", mode="before")(
        normalize_timestamp_to_int
    )


class RecordingErrorPayload(BaseModel):
    """
    Payload for recording.error webhook event.

    Reference: https://docs.daily.co/reference/rest-api/webhooks/events/recording-error
    """

    model_config = ConfigDict(extra="ignore")

    action: Literal["clourd-recording-err", "cloud-recording-error"] = Field(
        description="A string describing the event that was emitted (both variants are documented)"
    )
    error_msg: NonEmptyString = Field(description="The error message returned")
    instance_id: NonEmptyString = Field(
        description="The recording instance ID that was passed into the start recording command"
    )
    room_name: NonEmptyString = Field(
        description="The name of the room where the recording was made"
    )
    timestamp: int = Field(
        description="The Unix epoch time in seconds representing when the error was emitted"
    )

    _normalize_timestamp = field_validator("timestamp", mode="before")(
        normalize_timestamp_to_int
    )


class ParticipantJoinedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: NonEmptyString
    type: Literal["participant.joined"]
    id: NonEmptyString
    payload: ParticipantJoinedPayload
    event_ts: int

    _normalize_event_ts = field_validator("event_ts", mode="before")(
        normalize_timestamp_to_int
    )


class ParticipantLeftEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: NonEmptyString
    type: Literal["participant.left"]
    id: NonEmptyString
    payload: ParticipantLeftPayload
    event_ts: int

    _normalize_event_ts = field_validator("event_ts", mode="before")(
        normalize_timestamp_to_int
    )


class RecordingStartedEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: NonEmptyString
    type: Literal["recording.started"]
    id: NonEmptyString
    payload: RecordingStartedPayload
    event_ts: int

    _normalize_event_ts = field_validator("event_ts", mode="before")(
        normalize_timestamp_to_int
    )


class RecordingReadyEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: NonEmptyString
    type: Literal["recording.ready-to-download"]
    id: NonEmptyString
    payload: RecordingReadyToDownloadPayload
    event_ts: int

    _normalize_event_ts = field_validator("event_ts", mode="before")(
        normalize_timestamp_to_int
    )


class RecordingErrorEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    version: NonEmptyString
    type: Literal["recording.error"]
    id: NonEmptyString
    payload: RecordingErrorPayload
    event_ts: int

    _normalize_event_ts = field_validator("event_ts", mode="before")(
        normalize_timestamp_to_int
    )


DailyWebhookEventUnion = Annotated[
    Union[
        ParticipantJoinedEvent,
        ParticipantLeftEvent,
        RecordingStartedEvent,
        RecordingReadyEvent,
        RecordingErrorEvent,
    ],
    Field(discriminator="type"),
]
