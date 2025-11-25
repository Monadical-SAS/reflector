import uuid
from datetime import datetime
from typing import Any, Dict, Literal, Optional

from reflector.db.rooms import Room
from reflector.utils.string import NonEmptyString
from reflector.video_platforms.base import (
    ROOM_PREFIX_SEPARATOR,
    MeetingData,
    SessionData,
    VideoPlatformClient,
    VideoPlatformConfig,
)

MockPlatform = Literal["mock"]


class MockPlatformClient(VideoPlatformClient):
    PLATFORM_NAME: MockPlatform = "mock"

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._webhook_calls: list[Dict[str, Any]] = []

    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        meeting_id = str(uuid.uuid4())
        room_name = f"{room_name_prefix}{ROOM_PREFIX_SEPARATOR}{meeting_id[:8]}"
        room_url = f"https://mock.video/{room_name}"
        host_room_url = f"{room_url}?host=true"

        self._rooms[room_name] = {
            "id": meeting_id,
            "name": room_name,
            "url": room_url,
            "host_url": host_room_url,
            "end_date": end_date,
            "room": room,
            "participants": [],
            "is_active": True,
        }

        return MeetingData.model_construct(
            meeting_id=meeting_id,
            room_name=room_name,
            room_url=room_url,
            host_room_url=host_room_url,
            platform="whereby",
            extra_data={"mock": True},
        )

    async def get_room_sessions(self, room_name: NonEmptyString) -> list[SessionData]:
        if room_name not in self._rooms:
            return []

        room_data = self._rooms[room_name]
        return [
            SessionData(
                session_id=room_data["id"],
                started_at=datetime.utcnow(),
                ended_at=None if room_data["is_active"] else datetime.utcnow(),
            )
        ]

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        if room_name in self._rooms:
            self._rooms[room_name]["logo_path"] = logo_path
            return True
        return False

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        return signature == "valid"

    def add_participant(
        self, room_name: str, participant_id: str, participant_name: str
    ):
        if room_name in self._rooms:
            self._rooms[room_name]["participants"].append(
                {
                    "id": participant_id,
                    "name": participant_name,
                    "joined_at": datetime.utcnow().isoformat(),
                }
            )

    def trigger_webhook(self, event_type: str, data: Dict[str, Any]):
        self._webhook_calls.append(
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_webhook_calls(self) -> list[Dict[str, Any]]:
        return self._webhook_calls.copy()

    def clear_data(self):
        self._rooms.clear()
        self._webhook_calls.clear()
