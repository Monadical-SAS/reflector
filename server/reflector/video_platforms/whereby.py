import hmac
import json
import re
import time
from datetime import datetime
from hashlib import sha256
from typing import Any, Dict, Optional

import httpx

from reflector.db.rooms import Room

from .base import MeetingData, VideoPlatformClient, VideoPlatformConfig


class WherebyClient(VideoPlatformClient):
    """Whereby video platform implementation."""

    PLATFORM_NAME = "whereby"
    TIMEOUT = 10  # seconds
    MAX_ELAPSED_TIME = 60 * 1000  # 1 minute in milliseconds

    def __init__(self, config: VideoPlatformConfig):
        super().__init__(config)
        self.headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Authorization": f"Bearer {config.api_key}",
        }

    async def create_meeting(
        self, room_name_prefix: str, end_date: datetime, room: Room
    ) -> MeetingData:
        """Create a Whereby meeting."""
        data = {
            "isLocked": room.is_locked,
            "roomNamePrefix": room_name_prefix,
            "roomNamePattern": "uuid",
            "roomMode": room.room_mode,
            "endDate": end_date.isoformat(),
            "fields": ["hostRoomUrl"],
        }

        # Add recording configuration if cloud recording is enabled
        if room.recording_type == "cloud":
            data["recording"] = {
                "type": room.recording_type,
                "destination": {
                    "provider": "s3",
                    "bucket": self.config.s3_bucket,
                    "accessKeyId": self.config.aws_access_key_id,
                    "accessKeySecret": self.config.aws_access_key_secret,
                    "fileFormat": "mp4",
                },
                "startTrigger": room.recording_trigger,
            }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.config.api_url}/meetings",
                headers=self.headers,
                json=data,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            result = response.json()

        return MeetingData(
            meeting_id=result["meetingId"],
            room_name=result["roomName"],
            room_url=result["roomUrl"],
            host_room_url=result["hostRoomUrl"],
            platform=self.PLATFORM_NAME,
            extra_data=result,
        )

    async def get_room_sessions(self, room_name: str) -> Dict[str, Any]:
        """Get Whereby room session information."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.config.api_url}/insights/room-sessions?roomName={room_name}",
                headers=self.headers,
                timeout=self.TIMEOUT,
            )
            response.raise_for_status()
            return response.json()

    async def delete_room(self, room_name: str) -> bool:
        """Whereby doesn't support room deletion - meetings expire automatically."""
        return True

    async def upload_logo(self, room_name: str, logo_path: str) -> bool:
        """Upload logo to Whereby room."""
        async with httpx.AsyncClient() as client:
            with open(logo_path, "rb") as f:
                response = await client.put(
                    f"{self.config.api_url}/rooms/{room_name}/theme/logo",
                    headers={
                        "Authorization": f"Bearer {self.config.api_key}",
                    },
                    timeout=self.TIMEOUT,
                    files={"image": f},
                )
                response.raise_for_status()
        return True

    def verify_webhook_signature(
        self, body: bytes, signature: str, timestamp: Optional[str] = None
    ) -> bool:
        """Verify Whereby webhook signature."""
        if not signature:
            return False

        matches = re.match(r"t=(.*),v1=(.*)", signature)
        if not matches:
            return False

        ts, sig = matches.groups()

        # Check timestamp to prevent replay attacks
        current_time = int(time.time() * 1000)
        diff_time = current_time - int(ts) * 1000
        if diff_time >= self.MAX_ELAPSED_TIME:
            return False

        # Verify signature
        body_dict = json.loads(body)
        signed_payload = f"{ts}.{json.dumps(body_dict, separators=(',', ':'))}"
        hmac_obj = hmac.new(
            self.config.webhook_secret.encode("utf-8"),
            signed_payload.encode("utf-8"),
            sha256,
        )
        expected_signature = hmac_obj.hexdigest()

        try:
            return hmac.compare_digest(
                expected_signature.encode("utf-8"), sig.encode("utf-8")
            )
        except Exception:
            return False
