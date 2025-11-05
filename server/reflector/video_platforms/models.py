from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, Field

from reflector.schemas.platform import Platform

RecordingType = Literal["none", "local", "cloud"]


class MeetingData(BaseModel):
    platform: Platform
    meeting_id: str = Field(description="Platform-specific meeting identifier")
    room_url: str = Field(description="URL for participants to join")
    host_room_url: str = Field(description="URL for hosts (may be same as room_url)")
    room_name: str = Field(description="Human-readable room name")
    extra_data: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "platform": "whereby",
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
