import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from reflector.db.rooms import Room

from .base import MeetingData, Platform, VideoPlatformClient, VideoPlatformConfig


class MockPlatformClient(VideoPlatformClient):
    PLATFORM_NAME: Platform = "whereby"

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        # Store created rooms for testing
        self._rooms: Dict[str, Dict[str, Any]] = {}
        self._webhook_calls: list[Dict[str, Any]] = []

    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        """Create a mock meeting."""
        meeting_id = str(uuid.uuid4())
        room_name = f"{room_name_prefix}-{meeting_id[:8]}"
        room_url = f"https://mock.video/{room_name}"
        host_room_url = f"{room_url}?host=true"

        # Store room data for later retrieval
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
            platform="mock",
            extra_data={"mock": True},
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get mock room session information."""
        if room_name not in self._rooms:
            return {"error": "Room not found"}

        room_data = self._rooms[room_name]
        return {
            "roomName": room_name,
            "sessions": [
                {
                    "sessionId": room_data["id"],
                    "startTime": datetime.utcnow().isoformat(),
                    "participants": room_data["participants"],
                    "isActive": room_data["is_active"],
                }
            ],
        }

    async def delete_room(self, room_name: str) -> bool:
        """Delete a mock room."""
        if room_name in self._rooms:
            self._rooms[room_name]["is_active"] = False
            return True
        return False

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """Mock logo upload."""
        if room_name in self._rooms:
            self._rooms[room_name]["logo_path"] = logo_path
            return True
        return False

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Mock webhook signature verification."""
        # For testing, accept signature == "valid"
        return signature == "valid"

    # Mock-specific methods for testing

    def add_participant(
        self, room_name: str, participant_id: str, participant_name: str
    ):
        """Add a participant to a mock room (for testing)."""
        if room_name in self._rooms:
            self._rooms[room_name]["participants"].append(
                {
                    "id": participant_id,
                    "name": participant_name,
                    "joined_at": datetime.utcnow().isoformat(),
                }
            )

    def trigger_webhook(self, event_type: str, data: Dict[str, Any]):
        """Trigger a mock webhook event (for testing)."""
        self._webhook_calls.append(
            {
                "type": event_type,
                "data": data,
                "timestamp": datetime.utcnow().isoformat(),
            }
        )

    def get_webhook_calls(self) -> list[Dict[str, Any]]:
        """Get all webhook calls made (for testing)."""
        return self._webhook_calls.copy()

    def clear_data(self):
        """Clear all mock data (for testing)."""
        self._rooms.clear()
        self._webhook_calls.clear()
