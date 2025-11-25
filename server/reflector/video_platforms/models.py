from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from reflector.schemas.platform import WHEREBY_PLATFORM, Platform
from reflector.utils.string import NonEmptyString

RecordingType = Literal["none", "local", "cloud"]


class SessionData(BaseModel):
    """Platform-agnostic session data.

    Represents a participant session in a meeting room, regardless of platform.
    Used to determine if a meeting is still active or has ended.
    """

    session_id: NonEmptyString = Field(description="Unique session identifier")
    started_at: datetime = Field(description="When session started (UTC)")
    ended_at: datetime | None = Field(
        description="When session ended (UTC), None if still active"
    )


class MeetingData(BaseModel):
    platform: Platform
    meeting_id: NonEmptyString = Field(
        description="Platform-specific meeting identifier"
    )
    room_url: NonEmptyString = Field(description="URL for participants to join")
    host_room_url: NonEmptyString = Field(
        description="URL for hosts (may be same as room_url)"
    )
    room_name: NonEmptyString = Field(description="Human-readable room name")
    extra_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "platform": WHEREBY_PLATFORM,
                "meeting_id": "12345678",
                "room_url": "https://subdomain.whereby.com/room-20251008120000",
                "host_room_url": "https://subdomain.whereby.com/room-20251008120000?roomKey=abc123",
                "room_name": "room-20251008120000",
            }
        }


class VideoPlatformConfig(BaseModel):
    api_key: str
    webhook_secret: str
    api_url: Optional[str] = None
    subdomain: Optional[str] = None  # Whereby/Daily subdomain
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    # Whereby uses access keys, Daily uses IAM role
    aws_access_key_id: Optional[str] = None
    aws_access_key_secret: Optional[str] = None
    aws_role_arn: Optional[str] = None
