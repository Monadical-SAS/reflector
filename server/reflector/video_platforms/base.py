from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel

from reflector.db.rooms import Room


class MeetingData(BaseModel):
    """Standardized meeting data returned by all platforms."""

    meeting_id: str
    room_name: str
    room_url: str
    host_room_url: str
    platform: str
    extra_data: Dict[str, Any] = {}  # Platform-specific data


class VideoPlatformConfig(BaseModel):
    """Configuration for a video platform."""

    api_key: str
    webhook_secret: str
    api_url: Optional[str] = None
    subdomain: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_region: Optional[str] = None
    aws_role_arn: Optional[str] = None
    aws_access_key_id: Optional[str] = None
    aws_access_key_secret: Optional[str] = None


class VideoPlatformClient(ABC):
    """Abstract base class for video platform integrations."""

    PLATFORM_NAME: str = ""

    def __init__(self, config: VideoPlatformConfig):
        self.config = config

    @abstractmethod
    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        """Create a new meeting room."""
        pass

    @abstractmethod
    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get session information for a room."""
        pass

    @abstractmethod
    async def delete_room(self, room_name: str) -> bool:
        """Delete a room. Returns True if successful."""
        pass

    @abstractmethod
    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """Upload a logo to the room. Returns True if successful."""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Verify webhook signature for security."""
        pass

    def format_recording_config(self, room: Room) -> Dict[str, Any]:
        """Format recording configuration for the platform.
        Can be overridden by specific implementations."""
        if room.recording_type == "cloud" and self.config.s3_bucket:
            return {
                "type": room.recording_type,
                "bucket": self.config.s3_bucket,
                "region": self.config.s3_region,
                "trigger": room.recording_trigger,
            }
        return {"type": room.recording_type}
