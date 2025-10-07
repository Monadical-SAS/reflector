import hmac
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Optional

import httpx

from reflector.db.rooms import Room

from .base import MeetingData, VideoPlatformClient, VideoPlatformConfig


class DailyCoClient(VideoPlatformClient):
    """Daily.co video platform implementation."""

    PLATFORM_NAME = "dailyco"
    TIMEOUT = 10  # seconds
    BASE_URL = "https://api.daily.co/v1"

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        """Create a Daily.co room."""
        room_name = f"{room_name_prefix}-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        data = {
            "name": room_name,
            "privacy": "private" if room.is_locked else "public",
            "properties": {
                "enable_recording": room.recording_type
                if room.recording_type != "none"
                else False,
                "enable_chat": True,
                "enable_screenshare": True,
                "start_video_off": False,
                "start_audio_off": False,
                "exp": int(end_date.timestamp()),
            },
        }

        # Configure S3 bucket for cloud recordings
        if room.recording_type == "cloud" and self.config.s3_bucket:
            data["properties"]["recordings_bucket"] = {
                "bucket_name": self.config.s3_bucket,
                "bucket_region": self.config.s3_region,
                "assume_role_arn": self.config.aws_role_arn,
                "allow_api_access": True,
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/rooms",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

        # Format response to match our standard
        room_url = result["url"]

        return MeetingData(
            meeting_id=result["id"],
            room_name=result["name"],
            room_url=room_url,
            host_room_url=room_url,
            platform=self.PLATFORM_NAME,
            extra_data=result,
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get Daily.co room information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/rooms/{room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def get_room_presence(self, room_name: str) -> Dict[str, Any]:
        """Get real-time participant data - Daily.co specific feature."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/rooms/{room_name}/presence",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def delete_room(self, room_name: str) -> bool:
        """Delete a Daily.co room."""
        async with httpx.AsyncClient() as client:
            response = await client.delete(
                f"{self.BASE_URL}/rooms/{room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            # Daily.co returns 200 for success, 404 if room doesn't exist
            return response.status_code in (200, 404)

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """Daily.co doesn't support custom logos per room - this is a no-op."""
        return True

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Verify Daily.co webhook signature."""
        expected = hmac.new(
            self.config.webhook_secret.encode(), body, sha256
        ).hexdigest()

        try:
            return hmac.compare_digest(expected, signature)
        except Exception:
            return False
