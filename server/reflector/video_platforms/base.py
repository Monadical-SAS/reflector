from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional

from ..schemas.platform import Platform
from ..utils.string import NonEmptyString
from .models import MeetingData, VideoPlatformConfig

if TYPE_CHECKING:
    from reflector.db.rooms import Room

# separator doesn't guarantee there's no more "ROOM_PREFIX_SEPARATOR" strings in room name
ROOM_PREFIX_SEPARATOR = "-"


class VideoPlatformClient(ABC):
    PLATFORM_NAME: Platform

    def __init__(self, config: VideoPlatformConfig):
        self.config = config

    @abstractmethod
    async def create_meeting(
        self, room_name_prefix: NonEmptyString, end_date: datetime, room: "Room"
    ) -> MeetingData:
        pass

    @abstractmethod
    async def get_room_sessions(self, room_name: str) -> List[Any] | None:
        pass

    @abstractmethod
    async def delete_room(self, room_name: str) -> bool:
        pass

    @abstractmethod
    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        pass

    @abstractmethod
    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        pass

    def format_recording_config(self, room: "Room") -> Dict[str, Any]:
        if room.recording_type == "cloud" and self.config.s3_bucket:
            return {
                "type": room.recording_type,
                "bucket": self.config.s3_bucket,
                "region": self.config.s3_region,
                "trigger": room.recording_trigger,
            }
        return {"type": room.recording_type}
