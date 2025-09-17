import hmac
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Optional

import httpx

from reflector.db.rooms import Room, VideoPlatform
from reflector.settings import settings

from ..base import MeetingData, VideoPlatformClient


class WherebyClient(VideoPlatformClient):
    PLATFORM_NAME = VideoPlatform.WHEREBY

    def __init__(self, config):
        super().__init__(config)
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {self.config.api_key}",
        }
        self.timeout = 10

    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        data = {
            "isLocked": room.is_locked,
            "roomNamePrefix": room_name_prefix,
            "roomNamePattern": "uuid",
            "roomMode": room.room_mode,
            "endDate": end_date.isoformat(),
            "recording": {
                "type": room.recording_type,
                "destination": {
                    "provider": "s3",
                    "bucket": settings.RECORDING_STORAGE_AWS_BUCKET_NAME,
                    "accessKeyId": self.config.aws_access_key_id,
                    "accessKeySecret": self.config.aws_access_key_secret,
                    "fileFormat": "mp4",
                },
                "startTrigger": room.recording_trigger,
            },
            "fields": ["hostRoomUrl"],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.api_url}/meetings",
                headers=self.headers,
                json=data,
                timeout=self.timeout,
            )
            response.raise_for_status()
            meeting_data = response.json()

        return MeetingData(
            meeting_id=meeting_data["meetingId"],
            room_name=meeting_data["roomName"],
            room_url=meeting_data["roomUrl"],
            host_room_url=meeting_data["hostRoomUrl"],
            platform=self.PLATFORM_NAME,
            extra_data={
                "startDate": meeting_data["startDate"],
                "endDate": meeting_data["endDate"],
                "recording": meeting_data.get("recording", {}),
            },
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.config.api_url}/insights/room-sessions?roomName={room_name}",
                headers=self.headers,
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

    async def delete_room(self, room_name: str) -> bool:
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        try:
            async with httpx.AsyncClient() as client:
                with open(logo_path, "rb") as f:
                    response = await client.put(
                        f"{self.config.api_url}/rooms{room_name}/theme/logo",
                        headers={
                            "Authorization": f"Bearer {self.config.api_key}",
                        },
                        timeout=self.timeout,
                        files={"image": f},
                    )
                    response.raise_for_status()
            return True
        except Exception:
            return False

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        if not signature or not self.config.webhook_secret:
            return False

        try:
            expected = hmac.new(
                self.config.webhook_secret.encode(), body, sha256
            ).hexdigest()
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False
